# ALV-328 - Security and privacy requirements

Written 12 Nov 2026, before the spec, by `hrms-security-privacy-engineer`. Inputs:
`01-product-brief.md`, `02-design.md` (agreed by Surbhi 12 Nov 2026), and the code on
branch `slice/alv-326-shift-hours` (HEAD `4ae8499a`, which is also `origin/dev`).
Nothing was run against an API. Read-only SQL was run on the local demo site
`ppj.localhost` only. DTC was not checked.

**Size of this slice:** two existing endpoints return two to five more values per day, and
two existing screens show them. Nothing new is stored. The requirements below are sized to
that.

---

## 0 · Answers to the four questions

### Q1. Can a plain staff login read a colleague's "why" today? **No. No live finding.**

**Verified in code**, not by running it:

- The field is `alvoraa_rules_why`, Small Text, permlevel 0 (`payroll_fields.py:98`). Anyone
  who may read an Attendance row reads the reason with it.
- Attendance gives the Employee role read, share and print (`hrms/hr/doctype/attendance/attendance.json`;
  on the PPJ demo site Custom DocPerm also gives read and share, with report and export off).
- Every plain staff login carries one User Permission: Employee = its own record, "all
  document types" (`own_record_permission.py:84-104`). Attendance links Employee, so Frappe
  limits `/api/resource/Attendance` (list and get), `frappe.client.get_value` / `get_list`
  and `frappe.desk.reportview.get` to the person's own rows. The portal is not the limit here.
- Read-only count on `ppj.localhost`: **0** active, enabled staff logins without that row
  and without an HR-type role.

**When it would fail open** (pre-existing, not caused by this slice):

- A login that lost its own-record row. `run_once`'s "due a row but without one" count is
  the only detector (ALV-249 security review, item 3).
- A login holding a non-HR role that reads Employee (DTC: Location Manager, 5 logins; PPJ
  demo: 1 Payroll or Recruitment User). By design it gets no own-record row
  (`own_record_permission.excluded_roles`). Its Attendance read then depends on the narrow rows from `manager_scope.py`.
  **Unknown** for DTC. See Worry W1.

### Q2. Do month() and person() scope managers and HR correctly? **Yes for managers. HR has one gap, which is not new.**

| Path | Manager | HR |
|---|---|---|
| `attendance_correction.month()` through `_subject` (`attendance_correction.py:338-385`) | Own record, or anyone in `_reports_to(me, deep=True)`: direct **and indirect** reports, Active only (`attendance_analytics.py:100-117`). The caller must be an Active Employee (`:267-275`), so a leaver's login gets nothing. The Attendance read is `frappe.get_list` (`:485`). | Anyone with `submit` on Attendance Request. Narrowed by `_refuse_outside_scope` (`:297-335`) to `permitted_companies()`, or else to Branch permissions. **If an HR login has no Company permission, no Active Employee record and no Branch permission, nothing narrows it: it opens anyone on the site.** The code comment says this is on purpose (central HR). |
| `attendance_analytics.person()` (`attendance_analytics.py:601-625`) | Same deep list, Active only. | Only with an org role, and only inside the caller's **own Employee company** (`_in_organisation`, `:585-598`, read with `get_list`). An HR login with no Employee record is refused. Stricter than month(). |

**Verified in code:** a manager's Frappe doors match month(). The own-record row on the
Employee tree reaches every descendant, so `/api/resource/Attendance` gives a manager the
same days and reasons month() gives. Nothing is widened.

**One mismatch the design missed (verified in code):** punches are **direct reports only**
for a manager (`field_app_access.checkin_query_conditions`, `:190-212`). Attendance is the
whole tree. month() reads punches with `get_list` (`attendance_correction.py:516`), so for an
**indirect** report a manager sees the day and its reason, but no punches. A break worked
out from those empty punches would be wrong, or would say "a punch is missing". This is
question Q-1 below. It changes SEC-3.

### Q3. Break on lists. **Stated as PRIV-1.**

Honest limit: the stored reason **already says "Breaks: 55 minutes ..."** (ALV-326,
`payroll_rules.py:206`). HR User has export on Attendance (`attendance.json`, and on the
PPJ demo Custom DocPerm). So HR can export a company's reasons, break minutes included,
through Frappe's report view. A manager can list the whole tree's reasons through
`/api/resource/Attendance`. Each record is one they may already see. PRIV-1 controls what
**we build**. It cannot stop someone putting together a list from records they are allowed
to read. See Q-2 and the residual risk.

### Q4. Retention and DPDP. **Nothing new is stored.**

Break minutes are worked out at read time from Employee Checkin rows we already hold. The
reason and its date are already on Attendance (ALV-326 and earlier). So there is no new
retention question. Attendance and Checkin keep their current periods, and counsel has not
yet set a number for those (open, not this slice's). This slice **helps** with DPDP
transparency and with counsel's "access to automated decisions" advice: the person sees
why a day cost them. That closes ALV-326 security review M3.

---

## 1 · Threat model in four lines

1. **Who wants it:** a curious colleague wants another person's break (cheapest way: the API
   with a colleague's ID). A manager wants to rank the team on breaks (cheapest way: an
   API list of the tree's reasons).
2. **Blast radius of one mistake:** a missing scope check in month() or person() exposes one
   person's month at a time. A missing own-record row exposes the whole site. That one is
   outside this slice, and so is the HR cross-company gap.
3. **What it makes possible that was not before:** a per-day break figure on screen, and the
   reason, shown to the person themselves. Nothing new to a manager or HR that the API did
   not already give them. The new risk is a **structured** break value, which is easy to
   sort, should it ever reach a group view.
4. **How we would find out:** refused month() and person() calls are logged as SEC-17
   (`hrms.alvoraa_hr_core.access.refuse`). Frappe logs no successful list reads.

## 2 · Data inventory

| Item | Class | Purpose | Stored? | Retention | Who may see |
|---|---|---|---|---|---|
| `break_minutes`, `break_over`, `break_state` per day | Personal, work-behaviour | Explain the person's pay for a day | **No.** Worked out per request | None of its own (follows the punches) | The person, their manager (see Q-1), HR in scope |
| `alvoraa_rules_why` | Personal, pay-related | Same | Yes, already (Attendance) | Follows Attendance | Same; already readable by the same people through Frappe |
| `alvoraa_evaluated_on` | Low | Shows how old the reason is | Yes, already | Follows Attendance | Same |

**Must NOT see:** a colleague who is not the person's manager or HR. A manager outside the
person's line. HR outside their companies and branches. Anyone looking at a team,
department, branch or company view, where break must never appear.

## 3 · Obligations engaged

- **DPDP Act 2023 / Rules 2025:** purpose limitation and minimisation (worked out, not
  stored), reasonable safeguards (existing scoping). Baseline §2 last checked **24 Aug
  2026**, 80 days ago. Still in date, but stale on 22 Nov 2026. Not re-checked here,
  because this slice depends on no point of law.
- **Product rule FR-H7 / product-context §6 item 4:** no passive behavioural monitoring as
  a performance input. PRIV-1 puts this into practice.
- No counsel question blocks this slice.

## 4 · Abuse cases

- **Curious colleague:** calls `month(employee=<colleague>)`, `person(<colleague>)`, or
  `/api/resource/Attendance?fields=["alvoraa_rules_why"]&filters=[["employee","=",<colleague>]]`.
  Must get a refusal, or an empty list. SEC-1, SEC-4.
- **Over-scoped manager:** wants the team ranked by break. There must be no break on any team
  view, and no sort by it (PRIV-1). Opens an indirect report: the break must not be made up
  from punches they cannot read (SEC-3).
- **Departing employee:** an inactive Employee gets nothing from `_employee_for` / `_me`.
  ERPNext disables the login. Already covered and tested elsewhere; nothing new.
- **Guest:** both endpoints need a login. No public route is added.

## 5 · Requirements

**SEC-1 · The new values come only through month() and person(), after their existing check.**
No new whitelisted function, no new parameter. Break and reason are added inside the
function, after `_subject` (month) or the `allowed` check (person).
*Test:* a plain staff login A calls `month(employee=B)` and `person(B)` for colleague B →
`PermissionError`, and the response holds no `break_*` or `rules_why` key. The diff adds 0
`@frappe.whitelist`.

**SEC-2 · No new permission bypass.** The reason is read in the **existing** Attendance
`get_list` in month(). The punches person() needs are read with `frappe.get_list`, not
`get_all`, so `checkin_query_conditions` applies. No `ignore_permissions`.
*Test:* the `ignore_permissions` ceiling in `test_portal_security_010.CEILINGS` is unchanged
and green. Review the diff for any new `get_all` or `frappe.db.sql` on Attendance or
Employee Checkin.

**SEC-3 · A break is shown only when it comes from punches the caller may read.** If the
caller cannot read the person's punches (today: a manager looking at an indirect report),
show no break and no "a punch is missing". Never show a figure based on zero punches.
*Test:* manager M, direct report R1, indirect report R2, each with the same four punches on
one day. `month(R1)` → break figure. `month(R2)` → no break keys set, and no "missing"
state. Repeat for `person()`. *(Changes if Q-1 is answered "widen".)*

**SEC-4 · Frappe's own doors stay closed to a colleague for the reason.** As a plain staff
login (Employee role only), on a **freshly created site**:
`/api/resource/Attendance` list with `fields=["alvoraa_rules_why"]`, get of a colleague's
Attendance by name, `frappe.client.get_value("Attendance", <colleague's>, "alvoraa_rules_why")`
and `frappe.desk.reportview.get` all return nothing of the colleague's.
*Test:* one test per door. A negative check: delete the login's own-record User Permission
in the test, and the same call **must** return the colleague's row. If that check does not
fail, it proves nothing.

**SEC-5 · The reason is shown as text, never as HTML.** `acDetail` passes
`rules_why` and `evaluated_on` through `esc()` (`portal.js:215`).
*Test:* store `<img src=x onerror=alert(1)>` as a reason on a test row. The page shows it as
characters and no `img` element is created.

**PRIV-1 · Break appears only on one person's own days. It never appears on a group view.**
No `break` value in the response of `attendance_analytics.summary` (any view, any depth),
`filter_options`, `attendance_correction.team_days`, or any team, department, branch,
company or organisation list. No sort or filter by break. No break column on any group
table, and no break in any export or print we build. On Insights, Break exists only in
`person()`'s days.
*Test:* call `summary` for the mine, team and organisation views, plus `team_days`, as a
manager and as HR. Search each JSON response for any key containing "break" → none. A UI
check: the group tables have no Break column, and the one-person table has one.

**PRIV-2 · Nothing new is stored, cached or logged.** Break is worked out per request. No
new Custom Field, no `set_value`, no cache key, no copy on another DocType.
*Test:* the diff adds no Custom Field and no write. After migrate, Attendance's custom-field
count is unchanged.

**PRIV-3 · No break figure and no reason text in a log or an error message.** Refusals keep
today's SEC-17 entry, which carries an employee ID only. No `frappe.log_error`, logger or
`frappe.throw` contains break values or `rules_why`.
*Test:* review the diff for new log or throw calls. The SEC-17 refusal tests show the log
row with no break and no reason text.

**Release check, read-only counts on DTC (data-doors rule), before and after:** (a) active,
enabled logins due an own-record row but without one → must be 0. (b) Custom DocPerm on
Attendance for Employee, Location Manager, HR User and HR Manager (read, report, export,
share). (c) the Location Managers' User Permissions with `applicable_for = Attendance`. (d)
Attendance rows with `alvoraa_evaluated_on` set, by month. Count (d) is what must be
non-zero before anyone can see a reason on screen. Today it is **unknown**, and ALV-326 is
not on production, so DTC holds no "Breaks: N minutes" text yet.

## 6 · Questions

**Must know**

- **Q-1 · Indirect reports' break.** The design (AC-7) says a manager sees break for direct
  **and indirect** reports. The punch rule allows direct reports only. *Why it matters:* to
  show indirect reports' break, the punch rule (`checkin_query_conditions`) or month()'s
  punch read would have to widen. That is a decision about who sees whose punch times and
  places, not just a display change. *Question for Surbhi (via the BA):* "Should a manager
  see break for people two levels down, which means letting them see those people's punch
  times too?" *Default meanwhile:* no break for indirect reports (SEC-3). The reason still
  shows, as it does through the API today.

**Should know**

- **Q-2 · HR export of reasons.** HR can already export every day's reason, break minutes
  included, for the company. *Question for Surbhi:* "Do you accept that as HR's payroll
  record?" *Default:* no change in this slice, recorded as residual risk R1.

## 7 · Worries (not findings; each needs a check before it is one)

- **W1 · Location Managers at DTC (5 logins).** They hold no own-record row, by design. If
  they also hold no Attendance-scoped rows, the Employee role lets them read every
  Attendance row on the site, reasons included. ALV-249's notes (rule excludes them) and
  ALV-293's (their rows are untouched) do not agree with each other. *To check:* release
  count (c). Pre-existing.
- **W2 · HR company scope lives in portal code.** HR logins hold no Company User
  Permission (`attendance_correction.py:306-309` says so), so Frappe gives HR every
  company's Attendance. month() and person() narrow it in Python, and in two different
  ways. On a tenant with more than one company, that breaks the data-doors rule. Pre-existing.
  It is not widened here. Worth its own ticket.
- **W3 · A manager can share a report's Attendance day.** The Employee role has `share` on
  Attendance, and the tree row reaches reports. So a manager could open one day, reason
  included, to any colleague. It takes a deliberate act. Pre-existing.

## 8 · Residual risk

| # | Risk | Label | Owner | Accepted |
|---|---|---|---|---|
| R1 | Reasons with break minutes can be exported by HR, and listed through the API by a manager for their tree | Intentional trade-off (the reason must be readable to explain pay) | Surbhi | **Not yet accepted** - Q-2 |
| R2 | W1-W3 above | Temporary debt, outside this slice | Surbhi, via a ticket | Not yet accepted |

## 9 · What I could not check

- DTC's roles, Custom DocPerm and User Permission rows. This needs a read-only count on the
  tenant, run by whoever is allowed to (release check above).
- Any door by actually calling it. Every claim above is from reading the code or the local
  demo database. The SEC-4 tests are what will prove it.
- `ppj.localhost` does not have ALV-326's fields, so I could not see a real reason there.

## 10 · Subtract pass

Removed: an audit-log entry for each view of the reason (this is a read-only display of the
person's own record, and no obligation asks for it). A permlevel on `alvoraa_rules_why`
(it would hide the reason from the person too, or force a bypass in month()). A rate
limit. A DPIA (no new processing). A separate requirement for leavers (already covered and
tested). A Hindi or plain-words requirement (that is the product's call, not security's).

## Surbhi's answers (12 Nov 2026)

- **Q-1:** Managers do not see break for indirect reports by default. It can be an organisation setting, off by default. When on, the manager sees break (and therefore the punches behind it) for people further down the tree.
- **Q-2:** Accepted as recommended. HR's company-wide export of reasons, break minutes included, is HR's payroll record.

---

## Re-check, 12 Nov 2026 - the whole-line punch setting

By `hrms-security-privacy-engineer`, after `04-functional-spec.md` added the HR Settings tick
box `alvoraa_manager_sees_whole_line_punches` (Q-1 answer, then Q-A to Q-D accepted). Code
read in this worktree; Frappe and HRMS source read in the local bench container. Nothing was
run against an API. I wrote the requirements above, so this is the same author looking
again; the reviewer at `06` should check SEC-6 and SEC-7 with fresh eyes.

**Verdict: the spec's rule is sound, with two conditions.** (1) ALV-332 is fixed inside this
slice (SEC-7). (2) Surbhi is told that the photo log covers only Desk opens, not the API or
the photo file itself (SEC-11, Q-E), because her Q-A answer leaned on "photo views are logged".

### What the code says today (verified in code)

- `checkin_query_conditions` (`field_app_access.py:190-212`) and `checkin_has_permission`
  (`:215-231`) each work out "direct reports, Active" with their own query. Two copies.
- `checkin_has_permission` returns True for self and for a direct report **whatever `ptype`
  is asked** (`:229-231`).
- Employee Checkin gives the Employee role **read, write, create and delete**
  (`hrms/hr/doctype/employee_checkin/employee_checkin.json`, read in the bench).
- Frappe's `has_controller_permissions` (`frappe/permissions.py:483-500`) can only deny. So
  when our hook says True, the role's write and delete rights decide. That is why ALV-332 is
  real in shape: a direct manager's own-record User Permission covers the report (it reaches
  every descendant on the Employee tree), the role allows write and delete, and our hook says
  True. **Not run**: one `PUT` and one `DELETE` as a manager would prove it.
- `_reports_to(me, deep=True)` (`attendance_analytics.py:100-117`) keeps Active only at every
  level and cannot loop. `_viewer` (`field_app_access.py:182-188`) needs the caller to be an
  Active Employee.
- `log_photo_view` runs on `onload` (`hooks.py:195`). Frappe's REST read
  (`frappe/api/v1.py:74-88`) does not run `onload`, and nor does any list read. The photo is a
  private File attached to the checkin (`field_app_photos.py:105-113`), so its download is
  allowed by the checkin's read right **[Inference from Frappe's File rules; not traced
  line by line]**. Neither path writes a log row.
- HR Settings: HR Manager has write, nobody has import (`hr_settings.json`), `track_changes`
  is 1. The existing `validate_hr_settings` returns early when the field-app fields are
  missing (`field_app_settings.py:241-243`).
- Data Import cannot write HR Settings: no role holds `import` on it, and the importer saves
  through `doc.save()`, which runs `validate` anyway.

### ALV-332: fix it inside this slice. Yes.

This slice rewrites the same lines and must make the new deep branch read-only. Leaving the
direct branch as "True for any right" next to it puts two rules in one function: a skip-level
manager could not edit a punch, but a direct manager could edit or **delete** one. A deleted
punch changes pay. The fix is one condition on lines we are already changing. No feature needs
a manager to write a report's punch: I found no manager-session code path that saves or
deletes an Employee Checkin (the writes in `alv291_attendance_fix.py` and
`field_app_photos.py` run as system jobs). **[Inference: searched `alvoraa_portal` only]**

Out of scope, logged as a new worry (W4 below): the **self** branch also returns True for any
right, so a plain staff login may be able to edit or delete their **own** punches through
REST. It needs its own check and ticket. It is not made worse here.

### Added requirements

**SEC-6 · One rule, read in two places, giving the same set.** One function in
`field_app_access.py` answers "may C read P's punches". `checkin_query_conditions` and
`checkin_has_permission` both use it; month() and person() use it for the break. No second
copy of the walk.
*Test:* the AC-32 fixture (3 levels, a Left middle manager, an Inactive report), switch off
and on. For every manager, the set of people whose checkins `get_list` returns **equals** the
set for which `frappe.has_permission("Employee Checkin", "read", doc)` is True, checked record
by record. A test that compares only the list proves half.

**SEC-7 · The manager branch grants read only, direct and whole line (closes ALV-332's
manager half).** For a report (direct, or deep with the switch on), the hook returns True only
for `ptype` in `("read", "select")`. Any other right, or `ptype` None, returns False. HR roles,
self and the machine account stay as today.
*Test:* as direct manager M on report R's checkin: `PUT /api/resource/Employee Checkin/<name>`
→ 403, `DELETE` → 403, `frappe.client.set_value` → PermissionError, `frappe.client.delete` →
PermissionError. The same four as skip-level manager M2 with the switch on. Negative check:
with the `ptype` condition removed, the direct-manager `DELETE` must succeed - if it does not,
the test proves nothing. `GET` by name still returns 200 for both.

**SEC-8 · Leavers and inactive people stay out, at both ends.** With the switch on: a caller
whose Employee is not Active gets no one's punches (`_viewer` finds no employee). A person who
is Left, Inactive or Suspended is not in the set. A report under a Left or Inactive middle
manager is not reached.
*Test:* in the SEC-6 fixture, set one report Inactive and one Left; neither appears in the
list or passes `has_permission`. Set the top manager to Left; their list is empty.

**SEC-9 · Only a System Manager can change the setting, on every door.** The guard compares
old and new value (`cint`) and refuses when they differ and the session user lacks System
Manager. It must sit **before** the `F_ENABLED` early return in `validate_hr_settings`, or in
its own hook on the same event, so a site without the field-app fields is still guarded.
*Test:* AC-36's three doors, plus `frappe.client.save` with the whole HR Settings dict, plus a
`PUT` with only this field. Each → refused, value stays 0. Negative check: as System Manager
the same `PUT` succeeds. Data Import: one assertion that HR Manager's `can_import` does not
contain HR Settings.

**SEC-10 · The flip is in HR Settings' history.** A save that changes the field leaves a
Version row naming the user and showing 0 → 1 (or 1 → 0). This is Frappe's own
`track_changes`; build nothing.
*Test:* AC-29 and the reverse flip. A refused attempt leaves no Version row and no change.

**SEC-11 · The photo log still fires for the wider set, and we say honestly where it does
not.** With the switch on, a skip-level manager opening a punch with a photo in Desk leaves an
`Alvoraa Photo Access Log` row (AC-35). The setting's description and any wording to Surbhi or
a customer must **not** say "every photo view is logged": a REST `GET`, a list read with the
photo field, and the file download leave no row. This gap exists today for direct managers;
the setting widens it to the whole line.
*Test:* AC-35. Plus one test that records the gap: a REST `GET` of the same checkin leaves no
log row (so the day someone closes it, the test changes on purpose).

**PRIV-4 · Off by default, and off when unreadable.** Missing field, unreadable value or any
error → direct reports only. Read fresh on each request (no cache to clear).
*Test:* AC-28, AC-33, AC-34.

### Worries (added)

- **W4 · Staff may edit or delete their own punches through REST.** Same cause as ALV-332, on
  the self branch. Affects pay. *To check:* one `PUT` and one `DELETE` as a plain staff login
  on their own checkin. Pre-existing; its own ticket.
- **W5 · Photo download and API reads are not logged** (SEC-11). Closing it means a log in a
  File permission hook, or hiding the photo field by permission level. Bigger than this slice.

### Question for Surbhi (should know, does not block the build)

- **Q-E · Your Q-A answer accepted photos partly because photo views are logged. They are
  logged only when opened in Desk.** Do you still accept that, with the setting on, a
  skip-level manager can fetch a punch photo through the API or the file link with no log
  row? *Default meanwhile:* the setting ships off, and nobody turns it on at a tenant until
  you answer.

### Residual risk (added)

| # | Risk | Label | Owner | Accepted |
|---|---|---|---|---|
| R3 | With the setting on, skip-level photo and location reads outside Desk are not logged | Temporary debt (removed by W5's ticket) | Surbhi | **Not yet** - Q-E |
| R4 | Staff may edit or delete their own punches (W4) | Dangerous debt if confirmed - escalate on the first check | Surbhi, via a ticket | Not yet |

### Subtract pass

Removed: logging refused attempts to change the setting (the throw and the Version row are
enough; no obligation asks), a reason on the flip (the spec already dropped it), separate
requirements for link search and `get_count` (both go through `get_list`, so SEC-6 covers
them), and a fix for W4 inside this slice (not made worse here).

## Surbhi's answers to the re-check (12 Nov 2026)

- **Fold ALV-332 and ALV-333 into this slice: yes.** Outside HR, punches are read-only; staff may still create their own new punch (phone check-in); nobody outside HR edits or deletes a punch.
- **Q-E: yes.** She accepts that with the setting on, managers see photos for the whole line, knowing only Desk opens are logged (R3 accepted).

**DTC read-only check (step30, 12 Nov 2026):** Employee role has write/create/delete at level 0; time is level 1. In the last 120 days only Administrator (11) and the DTC admin login (4) deleted punches; 0 punch edits by non-HR users. Other roles with punch rights that the fix must not break: Biometric Sync (write, create), Location Manager (write, create), Payroll team and HR Data Officer.
