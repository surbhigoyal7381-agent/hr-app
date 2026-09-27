---
slice: 013-mobile-app
artifact: 03-implementation-notes-server-step2
author: hrms-fullstack-engineer
date: 2026-09-19
scope: STEP 2 of the server work - US-3 (the settings), the two codes step 1 declared, C-11c (company scoping of phone records), C-7 (email/print/share off)
branch: slice/013-mobile-app in .claude/worktrees/013-mobile-app, six commits on top of step 1's 3a45261
status: built and proven on test_site from a throwaway container. NOT in local dev. NOT pushed. No server touched.
update-2026-09-21: PUSHED. Now on origin/dev (confirmed at commit 146fa59), covered by
the same green CI "Python tests" run as steps 1, 3 and 4. See ALV-40 and ALV-33 on
YouTrack. The line above describes this step's state at the time it was written, not
its state today.
---

# 013 step 2 — what I built, what I proved, what is left

**Read this first — and see the update note above the frontmatter's `status`
line.** At the time this was written, nothing was in `dev` and nothing was
pushed. That is no longer the case — this step's code is on `origin/dev` and
has passed CI's database-backed test run. What follows is left as-written, as
the historical record of what was proven on `test_site` before that push.

---

## 1 · What I built, file by file

| File | New or changed | Mechanism | Why that one |
|---|---|---|---|
| `alvoraa_portal/field_app_settings.py` | **new** | build | The three settings read in one place, the validate/on_change hooks, the counts and history endpoint, and the installer. One eligibility function for E4/E5 now and E1/E3/E7 in step 3 |
| `.../doctype/alvoraa_field_worker_designation/` | **new** child table | configure | Frappe's `Table MultiSelect` needs a child doctype with one Link field (§4.4). Link to Designation, so a renamed or deleted designation is followed or refused by the framework |
| HR Settings custom fields `alvoraa_field_app_*`, `alvoraa_field_worker_designations`, `alvoraa_app_code_lifetime` | **new**, via `after_migrate` and `after_install` | configure | `CLAUDE.md` §4 puts organisation settings here. HR Settings already gives HR Manager write, HR User read, Employee read, and a Version row on every save - all four things US-3 needs |
| `alvoraa_portal/public/js/hr_settings_field_app.js` | **new** | build | The `fieldSettings` tab: live counts, retention line, change history; the `settingsOffConfirm` dialog; the remove-a-designation confirm. Prefixed `alvfa` so it cannot collide with hrms' own `hr_settings.js` on the same form |
| `alvoraa_portal/field_app_access.py` | changed | extend | `device_query_conditions` + `device_has_permission`, shaped like the check-in pair above them (C-11c) |
| `alvoraa_portal/field_checkin.py` | changed, 3 places | extend | `_refuse_unless_app_phone_is_eligible`, called in `field_status` (E4) and `field_checkin` (E5) |
| `alvoraa_portal/field_app_notice.py` | changed | extend | `retention_line()` pulled out of `rows_for` so the settings tab and the notice say the same words (AC-23) |
| `alvoraa_portal/hooks.py` | changed, append only | configure | `doctype_js` (new key); `doc_events["HR Settings"]` at the end of the dict; one line each at the end of `permission_query_conditions`, `has_permission`, `after_migrate`, `after_install` |
| `alvoraa_portal/subscription.py` | changed, 1 line | configure | The child table appended to `TENANT_DOCTYPES`, or `test_invoicing`'s "every Alvoraa doctype is classified" test fails |
| `.../doctype/alvoraa_field_device/alvoraa_field_device.json` | changed | configure | `email`, `print`, `share` removed from HR Manager and System Manager (C-7). `export` and `report` left as they were - nobody asked |
| `tests/test_field_app_step2_013.py` | **new** | build | 34 tests, section 6 |
| `tests/test_field_app_step1_013.py` | changed, 1 assertion | extend | AC-8's permission walk now also refuses email/print/share (C-7's pin) |
| `tests/test_portal_security_010.py` | changed, 1 row | extend | `CEILINGS` gains `field_app_settings.py` at 0 |

### Where the fields sit on HR Settings, and one deliberate difference from §4.5

The spec's §4.5 lists one `Section Break`. HR Settings is a tabbed form, and a section
break after its last field would land inside the **Recruitment** tab. So the fields sit
under their own **Tab Break** "Field attendance app" (the same shape `alvoraa_goals` used
for its review settings), and inside it three sections named as the approved design
`01b` §9.4 names them: *Who is a field worker* (the designation list), *The app* (the
switch, the code lifetime, the reason), *Photos and change history* (the HTML box). That
is three layout fields more than §4.5 lists and no data field more. The spec's fieldname
`alvoraa_field_app_section` is kept for the first section.

### The read path, exactly

`field_app_settings.settings()` does two `get_single_value(..., cache=False)` reads and
one `get_all` on the child table, every call. **No cache anywhere**, so there is nothing
to invalidate and a change is live on the next request - the step-1 probe measured this
read as fresh across worker processes with no restart. That is how AC-22's 60 seconds is
met, with margin. A read that raises for any reason - fields not installed, database
error - returns `enabled=False, designations=[]` and writes one Error Log row that names
no person. That is AC-21's "when HR Settings cannot be read → nobody", and it is tested
by patching the read to raise.

### The reason, exactly

`validate_hr_settings` (doc_events, so desk, REST and `frappe.client.set_value` all pass
through it) refuses a save that turns the switch off or drops a designation without a
reason from the fixed list, refuses a lifetime outside the six options, and refuses a
reason outside the list. `clear_reason_after_save` runs on `on_change`, which Frappe
calls **after** `save_version`, so the Version row holds the reason and the stored field
is then emptied with `update_modified=False`. The in-memory document is emptied too, so
the desk form is not handed back a reason the record no longer holds. This is the
`Alvoraa Leader View Settings` pattern, with that one addition.

The reason is a fixed list and not free text on purpose: the Employee role can read HR
Settings, and the change history is built from Version rows any System Manager can read,
so nothing here may ever be able to hold a name.

### The company scoping, exactly (C-11c)

`device_query_conditions(user)`:
- Administrator or System Manager → `""` (no filter).
- HR Manager / HR User → `permitted_companies(user)` from `hrms.alvoraa_hr_core.access`
  - the shared control every HR endpoint already uses: the user's Company User
  Permissions, else their own employee record's company, else nothing. Empty → `1=0`.
  Otherwise `` employee in (select name from `tabEmployee` where company in (...)) ``,
  with every company name through `frappe.db.escape`.
- Anyone else → `1=0` (nobody else has a role on the doctype; the fallback is silence).

`device_has_permission(doc, user)` answers the same question for one record by reading
the employee's company. Two hooks because they guard different doors: the list and
every report, and `/app/alvoraa-field-device/<name>` or `frappe.client.get`.

**One consequence to know:** an HR Manager with no Company User Permission and no
Employee record now sees **no** phones. Frappe's own Employee permission would show such
a user every employee. `permitted_companies` fails closed and every HR endpoint in the
product already behaves this way (SEC-13), so the phone list now matches them rather
than Frappe's looser default. Pinned by `test_013_hr_with_no_company_and_no_employee_record_sees_nothing`.

---

## 2 · The acceptance criteria, one by one

| AC | How it is satisfied | Proven? |
|---|---|---|
| AC-14 defaults on migrate; nothing else changes | `after_migrate` creates the fields, then seeds `enabled=1` and `lifetime="1 day"` **only where no Singles row exists** (a Check custom field's default is only applied to records created after the field exists; HR Settings already exists everywhere). Designations start empty. A test deletes the rows, runs the installer twice, and compares every other HR Settings row before and after | **proven** |
| AC-15 HR Manager saves; Version row | HR Settings' own DocPerm and `track_changes` | **proven** (owner and `changed` entry checked) |
| AC-16 HR User / Employee cannot save | HR Settings' own DocPerm: HR User read, Employee read | **proven** (`has_permission` False and `save()` raises for both) |
| AC-17 confirm with counts; reason required; server refuses too | Dialog in the form script with `waiting_codes`, `active_app_phones` and the exact sentences; `validate_hr_settings` refuses on the document and on `frappe.client.set_value` | server **proven**; dialog **hand-traced** (section 6) |
| AC-18 removing a designation: same confirm, server-enforced | `before_<field>_remove` / `<field>_remove` events of Table MultiSelect; server compares the before/after row sets | server **proven**; dialog **hand-traced** |
| AC-19 reason in the Version row, empty afterwards | `on_change` after `save_version` | **proven** |
| AC-20 lifetime outside the six options refused | Select options plus an explicit check; `"90 days"`, `"2 days"`, `"0"`, `"forever"` all refused through `set_value` | **proven** |
| AC-21 eligibility: listed / not / empty list / unreadable | `refuse_unless_eligible`; the unreadable case by patching `get_single_value` to raise | **proven** |
| AC-22 live within 60 s | No cache in the read path; `cache=False` | **proven in-process**; cross-process was step 1's measurement |
| AC-23 retention line, no link | `notice.retention_line()` shared with the notice; the HTML box has no link | **proven** (same string) |
| AC-24 last 20 changes to these fields, newest first, "HR cannot change this list." | `_history()` reads up to 200 Version rows for HR Settings in one query and keeps the ones touching our fields | **proven** |
| AC-25 live employee count | `settings_info(designations=<on-screen list>)`, one grouped query | **proven** against `frappe.db.count` |
| AC-78 an app phone is refused while off / not listed, restored with no new code, row unchanged | `_refuse_unless_app_phone_is_eligible` keyed on `join_method == "App QR code"` | **proven** (`status`, `modified`, `token_hash` compared before and after) |
| §3.5 web phones keep working | Same key | **proven** |
| AC-149 HR limited to one company sees one company's phones | The two hooks | **proven**, and **fails without the hooks** (section 6) |
| C-7 | JSON | **proven** in the step-1 permissions test |

### Not in step 2, deliberately

- **`waiting_codes` is always 0.** The code record (`Alvoraa App Invite`) is step 3. The
  helper says so rather than guessing at a doctype and a status name that do not exist.
- **The `notField` / `appOff` phone screens' words** are the app's. The server sends the
  code and, for `NOT_FIELD_ROLE`, the designation - the one value §7.1 allows. The
  `_server_messages` sentence is for logs and the web page only.
- **The Employee desk section (US-16) and E12's phone/code data** - step 5.
- **The join flow, the withdrawal action, anything that erases data** - not touched.
- **`deploy/nginx.conf`, `subscription.requires_feature`, any hrms index,
  `www/hrms-employee.html`, the old consent fields, `patches.txt`** - not touched. No
  patch was needed: the fields come from `after_migrate`, the permission change from the
  JSON, the defaults from the installer.

---

## 3 · The seven dimensions, re-assessed against the code I actually wrote

| Dimension | Before → after | Why |
|---|---|---|
| **Performance** | **degrades slightly, bounded** | E4 and E5 gain, **for app phones only**, three small reads per call (two Singles rows, one child-table list) plus one `Employee.designation` lookup on E5. Web phones - every phone that exists today - pay nothing: the key is `join_method`. The settings tab's counts are two grouped queries with a join and two `count()`s; the history is one query capped at 200 rows and filtered in Python. **No loop does a query.** The scoping subquery runs on every phone list for HR; `Employee.company` is indexed by ERPNext and `Alvoraa Field Device.employee` has `search_index`. Designed volume: 400 field workers, 2 punches a day, tens of HR Settings saves a year |
| **Security** | **improves** | The company hole closes (C-11c). `email`/`print`/`share` come off the phone record (C-7). `settings_info` is HR-only on the server (`_hr_only`), plan-gated, validates its one input (a JSON list of ≤200 strings of ≤140 chars), and answers only counts. `ignore_permissions`: **zero** new uses; `field_app_settings.py` is in `CEILINGS` at 0. The scoping SQL is built only from `frappe.db.escape`d company names; the counts use the query builder |
| **Reliability** | **improves** | Reads fail closed (AC-21). The two validate hooks on HR Settings each look only at their own fields, so neither can stop HR saving the page over the other's values - a test saves with both installed. The installer is safe to run twice and never overwrites a stored value. A refusal at E4/E5 changes nothing on the phone row, so restoring the setting restores the phone |
| **Scalability** | **neutral** | Nothing grows with headcount except the counts, which are grouped queries. Multi-tenant: one database per site, the settings are per site |
| **Maintainability** | **improves** | One eligibility function for every endpoint that will ever ask. The fieldnames are constants in one file. The history reads Frappe's own Version rows rather than keeping a second record that could disagree. The form script only asks; the server decides - so a screen change cannot weaken a rule |
| **Data integrity** | **improves** | The reason is recorded in the same Version row as the change it explains, then emptied so it cannot be reused. Only the six lifetimes exist. The installer seeds defaults where absent and touches nothing else (compared row for row in a test). No cache was added, so no invalidation can be wrong |
| **Compliance / privacy** | **improves** | The change history that Employee-role users can read holds a fixed-list reason, never free text. The refusal for a switched-off tenant is the same for everybody, so it does not say who is on the list. `NOT_FIELD_ROLE` carries the person's own designation and nothing else; the allowed list never reaches the phone (tested). No visibility widened: the counts are aggregates with no names, HR-only. **Visibility narrowed** for HR users limited to one company, which is the point |

---

## 4 · Things I found that the spec has wrong or unsettled

1. **§4.5 says one Section Break; the approved design says four sections.** I built the
   design's shape under a Tab Break (section 1). Layout only; every data field is as §4.5
   lists it. Somebody should reconcile the two documents.
2. **§8's "own-scope" definition and `permitted_companies` differ for one user shape.**
   §8 says own-scope is "only employees Frappe's own permission check lets that user
   read". For an HR Manager with no Company User Permission and no Employee record,
   Frappe's own check shows everyone; the shared control shows nobody. I went with the
   shared control - it is what SEC-13 chose for every HR endpoint and it fails closed -
   and pinned it. If the spec's wording was meant literally, that is a product decision.
3. **AC-17's counts include "codes waiting to be used", which cannot be counted until
   step 3.** The dialog shows 0 today, honestly. When `Alvoraa App Invite` exists,
   `_waiting_codes()` is the one place to fill in.
4. **The form script's `frappe.call` would pop the plan sentence as a dialog** on every
   HR Settings refresh for a tenant without field check-in (a 403 with
   `_server_messages` goes through Frappe's message display). Fixed with `silent: true`
   and the sentence written into the box instead (commit `5ef47cd`). Worth knowing for
   every desk endpoint E7-E12 will add: the desk shows refusals on its own unless told not
   to.
5. **`frappe.get_all(fields=["count(name) as n"])` is refused in Frappe v16** ("SQL
   functions are not allowed as strings in SELECT"). The first run caught it; the counts
   use the query builder. Anyone porting an older grouped count will hit the same wall.

---

## 5 · Three personas

| Persona | What changes | What must not change - and did not |
|---|---|---|
| **CXO / System Manager** | Sees the new tab on HR Settings and can change it; loses email/print/share on the phone record; still sees every company's phones | Their read of check-ins and photos; no way to unblock a phone appeared |
| **HR Manager** | Changes the three settings, with a reason when stopping something; sees counts and history; **now sees only their companies' phones** | Cannot see a code (none exist yet); the counts carry no names |
| **HR User** | Reads the tab, cannot save it (HR Settings' own permission); same company scoping | Nothing widened |
| **Employee (field worker)** | An app phone gets `APP_OFF_FOR_FIELD` / `NOT_FIELD_ROLE` when the org says so; a web phone is untouched | Never learns who is on the list; never learns a block reason |
| **Employee (office colleague)** | Can still read HR Settings (Frappe's default), sees the fields but no counts and no history (the box is HR-only, server and client) | No phone, code or acknowledgement row readable - no Employee role on any of them |

---

## 6 · What I ran, and the real numbers

All bench work from a throwaway container `hrlocal-013` mounting **this worktree's**
`alvoraa_portal`, `hrms` and `alvoraa_goals` against the shared `hrlocal-sites` volume,
on the `hrlocal` network, as user `frappe`. The bench container itself was idle throughout
(`pgrep -af run-tests` empty before I started). One run at a time. The bench claim was
on the work board from before the first bench command until after the last.

| Step | Command / check | Result |
|---|---|---|
| Static | `ast.parse` on every changed `.py`; `json.load` on both doctype JSONs; `node --check` on the JS | all parse |
| Static | `ruff check --config hrms/pyproject.toml` on my files | 2 findings of mine (UP030) fixed; 1 pre-existing on step 1's moved line 58, left alone |
| Static | `scripts/check_app_integrity.py` | **602 checks, OK** (592 at step 1; the new doctype and hooks add ten) |
| Static | `scripts/check_api_paths.py` | 2 unresolved - **both the known pre-existing hrms `payment_entry.js` debt**, same as step 1 |
| Baseline | Custom DocPerm on test_site | **228 rows / 45 doctypes** (unchanged from step 1) |
| Migrate | `bench --site test_site migrate` from the container | **2 min 24 s, 0 failed.** Child doctype `istable=1`; 9 custom fields on HR Settings; Singles seeded `alvoraa_field_app_enabled=1`, `alvoraa_app_code_lifetime=1 day`; device DocPerm email/print/share = 0 for all three roles, export kept |
| First run of the new module | `run-tests --module ...test_field_app_step2_013` | 27 + 7 tests, **4 errors**: the grouped count as a string (section 4 item 5). Fixed |
| Second run | same | 27 + 7, **1 error**: the test read `Singles` through `get_all` ("DocType Singles not found"). Test fixed to a parameterised query |
| Third run | same | **27 + 7 = 34 OK** |
| Step 1 module | `...test_field_app_step1_013` | **15 + 13 = 28 OK** (includes the new C-7 pin) |
| Slice 014 module | `...test_checkin_security_014` | **14 + 2 = 16 OK** |
| **Fail-without-fix (C-11c)** | The two `Alvoraa Field Device` lines removed from `hooks.py`; the site's `app_hooks` cache key dropped (`frappe.cache.delete_value("app_hooks")`, site-scoped, the same thing the migrate had done); the three scoping tests run | **FAILED (failures=4)**: `AssertionError: Items in the first set but not the second` three times (HR User, HR Manager, the no-company user each listed the other company's phone) and `'alvoraa_portal.field_app_access.device_query_conditions' not found in []`. `hooks.py` restored with `git checkout --`, cache key dropped again, re-run: **3 OK**. The broken state was never committed |
| Full `alvoraa_portal` | `run-tests --app alvoraa_portal` | _see 6.1_ |
| Full `alvoraa_goals` | `run-tests --app alvoraa_goals` | _see 6.1_ |
| test_site afterwards | Custom DocPerm | _see 6.1_ |

### 6.1 · The full suites

| Suite | Result |
|---|---|
| `bench --site test_site run-tests --app alvoraa_portal` | **604 + 700 = 1,304 tests, OK**, 0 failures, 0 errors, 4 skipped. 56 min 27 s. (Step 1's baseline was 1,270; the 34 new step-2 tests account for the difference exactly) |
| `bench --site test_site run-tests --app alvoraa_goals` | **18 OK**, 2 skipped. 42 s |
| Custom DocPerm on test_site | **228 rows / 45 doctypes before and after** - unchanged |
| HR Settings afterwards | `alvoraa_field_app_enabled=1`, `alvoraa_app_code_lifetime=1 day`, reason empty, designation list empty - the defaults, as found after the migrate |
| Container `hrlocal-013` | removed; bench claim cleared on the work board |

### 6.2 · The form script, traced by hand (no browser here)

Every client API used was read in Frappe v16.33.1's own source before use:
`frappe.ui.form.on` events including the `before_<field>_remove` / `<field>_remove` /
`<field>_add` triggers `ControlTableMultiSelect` fires on the parent form
(`table_multiselect.js:55-70, 176-180`); `frm.add_child`, `frm.refresh_field`,
`frm.is_dirty`, `frm.set_value`; `frappe.user.has_role` with a list (`user.js:46`);
`frappe.ui.Dialog` with `get_primary_btn` and `secondary_action`; `frappe.call` with
`silent` and `error` (`request.js:121, 417, 462`); `frappe.datetime.str_to_user`;
`frappe.utils.escape_html`.

Flows:
1. **Open the tab as HR.** `refresh` → snapshot of the saved state (form clean) → one
   call to `settings_info` with the on-screen list → box shows "{n} active employees have
   these designations.", the retention line, "HR cannot change this list." and the last
   20 changes. Every string goes through `escape_html`.
2. **Open as an Employee-role user.** Box is emptied, no call made. The server would refuse
   the call anyway (`_hr_only`).
3. **Tenant without field check-in.** Call refused 403 with the plan sentence; `silent`
   stops the dialog; the sentence is written into the box.
4. **Untick the switch.** Field event fires; saved state was on → dialog with the four
   lines and the reason select. *Keep it* → switch set back to 1 (the event fires again,
   saved is on and current is on, no dialog). *Turn off* with no reason → "Choose a
   reason. It is kept in the change history." and the dialog stays. With a reason → reason
   field set. Save → server accepts, records, empties the reason; `after_save` re-snapshots
   and redraws.
5. **Save with the switch off and no reason** (dialog dismissed with Escape) → `validate`
   shows the same sentence and blocks the save; the server would refuse it too.
6. **Remove a designation pill.** `before_..._remove` reads the designation while the row
   exists; `..._remove` redraws the count and, if that designation was in the saved list,
   asks with its own counts. *Keep it* → the row is added back and the field refreshed.
   *Remove* with a reason → reason set.
7. **Add a designation.** `..._add` redraws the count from the on-screen list.

Accessibility of what was built: the dialog is Frappe's (`role="dialog"`, focus moved into
it, Escape closes); the reason is a labelled Select with a description; the error text
says what to do; the count paragraph is `aria-live="polite"`; the history is a list with
an `aria-label`; the destructive button is red **and** says "Turn off" / "Remove", so
colour is not the only signal. Not measured at 200% zoom or on a phone - it is a desk
settings page and there is no browser in this session.

---

## 7 · What else moved while I worked

`git fetch origin dev`: **nothing new** - `origin/dev` is still `baa9f68`. Local `dev` has
three commits my base does not (`4f35960` runbook, `99a17a4` and `3f5ce3d` slice 024:
`auth.py`, one `get_website_user_home_page` line at the **top** of `hooks.py`, a new test,
docs). None of them touches a file I changed except `hooks.py`, and there in a different
place (the top; mine are at the ends of blocks), so a rebase will be clean. I did not
rebase: the instruction was to commit on the branch only, and the base is the one step 1
was proven on.

The main checkout's uncommitted changes (`ux-learnings.md`, `alvoraa_position.py`, the
KPI backlog, the 009 plan, several untracked documents) are other sessions' work in
progress. Not touched, not staged.

---

## 8 · Known gaps and shortcuts, declared

1. **The form script was traced, not run.** No browser in this session. The three dialog
   flows need one pass on the local instance by a person before this reaches dev.
2. **`waiting_codes` is 0 until step 3** (section 4 item 3).
3. **`export` and `report` stay on the phone record.** C-7 named email, print and share.
   An export is also a list of who carries which phone; nobody asked, so I did not decide
   it.
4. **The history reads at most 200 Version rows.** A tenant that saves HR Settings more
   than 200 times between two field-app changes would see fewer than 20 entries. Bounded
   on purpose; a dedicated index or a filtered column can come if a real tenant hits it.
5. **`permitted_companies` vs Frappe's own Employee scope** (section 4 item 2) - a
   decision recorded, not a defect.
6. **`test_site` now carries the step-2 schema.** Nothing on `dev` reads the new fields or
   the child table, so nothing there breaks; but anyone rebuilding test_site from `dev`
   will lose them and must migrate from this branch again before running these modules.
7. **One `app_hooks` cache key was dropped twice** on test_site during the fail-without-fix
   proof. It is site-scoped and rebuilt on the next read. Declared because the rule says
   cache clearing is asked for; this was the minimum needed to make the proof honest.
