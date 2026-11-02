# Slice 080 — implementation notes

One new `Employee` field, **"Alternative number"**. Her decision of 2 November
2026. Nothing else.

## What was built, file by file

| File | What changed | Mechanism | Why |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/alternative_number.py` | **New, 54 lines.** The field definition and `after_migrate()` | customise | One Custom Field on an existing DocType, created by the pattern this app already uses eight times. No DocType, no settings page, no registry |
| `alvoraa_portal/alvoraa_portal/hooks.py` | Two entries, one in `after_migrate`, one in `after_install`, both before `employee_field_rights.apply` | configure | Both lists, or the field is missing on one kind of tenant. See the patch finding below |
| `alvoraa_portal/alvoraa_portal/employee_field_rights.py` | One name added to `LEVEL_2` | extend | Without it the field is level 0 — readable by all and **writable by the employee** |
| `hrms/hrms/alvoraa_org_structure/people_fields.py` | The eleventh entry on `POSITIONS_PROFILE_FIELDS`; the stale "no work phone, a decision for Surbhi" comment replaced | extend | Nothing else in that file moved |
| `alvoraa_portal/alvoraa_portal/staff_api.py` | `ROW_FIELDS` and `ROW_KEYS`; the stale comment replaced | extend | The alias style follows `company_email as work_email` |
| `public/js/ess/portal.js` | One entry on `MPF_FIELDS` | extend | The drawer and the settings tick list read the same list, so one line serves both |
| `public/js/ess/next-frame.js` | The directory row draws the number as a `tel:` link | extend | Alongside the mail link, same escaping |

**No patch and no `patches.txt` entry.** See below.

Fieldname: **`alvoraa_alternative_number`**. The app's prefix for every custom
field it creates, so no collision with Frappe, ERPNext, Frappe HR or the India
regional pack — checked by grep over `erpnext/setup/doctype/employee`,
`hrms/regional` and `india_compliance`, not assumed.

Permission level: **2**. Read from the file, not from the names. Level 1 is
HR Manager only for **read** as well as write, so it would hide the number from
the colleagues it exists for. Level 2 gives read to every role that already
reads `Employee` and write to HR User, HR Manager and System Manager — which is
exactly "HR fills it in; the employee cannot; everyone in the company can see
it".

## Where the approved strategy was wrong

**A patch cannot create this field.** Frappe marks every patch as already done
when a site is built, so the patch would never run on a new tenant. The field
would be missing exactly where it is hardest to notice. The same lesson is
written in `employee_field_rights.py:17-21`.

So the field is created by `after_migrate` **and** `after_install`, the pattern
`payroll_fields.py` and `branch_scope.py` already use. There is no patch at
all: a third path to the same field would do nothing the two hooks do not, and
there is a test that fails if one appears.

This changes the mechanism, not anything Surbhi decided. It needs her note, not
her approval.

## The ACs

| What she asked for | How it is satisfied |
|---|---|
| A new field on `Employee` | `alternative_number.py`, created on every tenant by both hook lists |
| Labelled exactly "Alternative number" | `label` in the field definition; asserted on the live meta in Python and on `MPF_FIELDS` in the DOM suite |
| Her help text, her wording | The field's `description`, asserted character for character |
| HR fills it in; the employee cannot | permlevel 2. Two tests: the employee's own save keeps the old value, HR's save writes it |
| Tickable on the Positions page | The eleventh entry on `POSITIONS_PROFILE_FIELDS`; the picker offers it, asserted in the DOM suite |
| Ships off until a tenant ticks it | Nothing sets the default. `ticked_fields()` returns it only once ticked, asserted |
| In the staff directory, beside work email | `ROW_FIELDS` / `ROW_KEYS`, in the position straight after `work_email`, asserted on the payload keys |

**Satisfied with one caveat:** the help text is on the Employee form, not beside
the tick. See "What needs Surbhi".

## The seven dimensions, against the code actually written

| Dimension | Before → after | Why |
|---|---|---|
| Performance | neutral | One extra column on a query that already selects six, and one on a query that already selects ten. No new query, no new round trip. The directory's two-queries-whatever-the-size property is unchanged |
| Security | neutral | The write limit is a Property Setter in Frappe's own field-permission layer, not portal code. No new endpoint, no `ignore_permissions`, no raw SQL. `test_portal_security_010`'s bypass ceiling does not move |
| Reliability | neutral | `create_custom_fields` writes only what is missing and is guarded on the DocType existing. A blank value renders as nothing on both surfaces; `reports_to`-style special cases are not needed |
| Scalability | neutral | No per-person read added anywhere |
| Maintainability | **improves slightly** | Two comments that told the next reader "this is still a decision for Surbhi" now say what she decided. A test constant named `TEN` holding eleven items was renamed |
| Data integrity | neutral | A new nullable column. Nothing to migrate, nothing to backfill |
| Compliance / privacy | **widens visibility, deliberately, inside the rule already set** | A new personal value reaches colleagues. Allowed because her decision of 24 Sep 2026 put **work contact** in the directory, and a number the company hands out is the same class. It is not on `NEVER` because it is meant to be seen, and not on `MY_PROFILE_WRITE_FIELDS` because the employee does not own it — both asserted, so "we forgot" and "we decided" cannot look the same later |

## NFR notes

* **Query counts:** unchanged. Directory: 2. Positions profile: the same as
  before (one base read, one ticked-field read, one batched thumbnail read).
* **Indexes:** none added. Nothing filters or joins on this column.
* **Background jobs:** none.
* **Permission enforcement points:** the Property Setter at permlevel 2 (Frappe
  enforces it on every document save, through every door); `refuse_own_locked_change`
  for HR's own record, which already covers every high-permlevel field;
  `refuse_import_of_locked_columns` for Data Import; the allow-list
  intersection at the Positions setter and again at the Positions reader.
* **Sensitive fields touched:** this one, and no other. The number is published
  to colleagues on purpose; nothing in `NEVER` moved.
* **One thing worth naming precisely:** a permission **level does not refuse a
  READ through `frappe.get_all`** — Frappe's `db_query` has no permlevel
  filtering. That is already written down in `people_fields.py` and is why the
  allow-list, not the level, is the control on what the Positions page shows.
  For this field a wide read is what was asked for, so the level is carrying
  only the write half, which is the half her decision needed.
* **Fallbacks:** no value means no row in the drawer ("Not recorded") and no
  link on the directory row. No error, no placeholder.

## What else moved while I worked

`origin/dev` was at `b202a37d` when I branched and at `b202a37d` when I
committed — slice 079's five commits had already landed. **Nothing came in
while I worked, so there were no conflicts to resolve.** Fetched again
immediately before the commit, as the rule requires.

## Commands run, and what they said

Full output lives in the bench's `sites/` folder as `r_<module>.log`, read with
`grep -aE "^Ran |^OK|^FAILED"` rather than tailed, because `bench run-tests`
prints more than one batch summary.

| Suite | Result |
|---|---|
| `alvoraa_portal.tests.test_alternative_number_080` (new) | `Ran 13 / OK` (12 after the subtract pass) |
| `test_my_photo_078` | `Ran 35 / OK` |
| `test_mini_profile_078` | `Ran 12 / OK` |
| `test_people_settings_078` | `Ran 22 / OK` |
| `test_faces_078` | `Ran 8 / OK` |
| `test_employee_field_rights_alv215` | `Ran 20 / OK` |
| `test_staff_list_034` | `Ran 11 / OK` then `Ran 22 / OK` (two batches) |
| `test_directory_contact_045` | `Ran 17 / OK` |
| `test_portal_security_010` | `Ran 45 / OK` then `Ran 5 / OK` (two batches) |
| All 21 jsdom suites | `DOM tests: 21 run, 0 not run, 0 failed` |
| `test_joiner_079` | **Could not be run to a conclusion on this bench — and not because of this slice.** Stopped at 25 of 57 tests. Every failure is on the `_sign_in()` path and the error is `AttributeError: 'AlvoraaJoinerSubmission' object has no attribute 'user'`, raised inside slice 079's own `make_sign_in`. The `user` field IS in that DocType's JSON on this branch; the **site's schema had not been synced to it**. `git diff origin/dev` for every joiner file and for the whole doctype folder is empty, and `test_the_joiner_candidate_list_is_the_same_six_by_identity` — the one joiner test that reads `people_fields` and makes no sign-in — **passed**. The regression this slice could actually cause is pinned in the new suite (`assertIs` on all three joiner keys) and in `test_my_photo_078`, both green |

**The guards were broken on purpose.** With the one `LEVEL_2` line removed,
five of the new tests fail, including
`test_alt080_an_employee_cannot_write_their_own_alternative_number` — so the
permission is being proved, not described. The line was put back and the suite
is green again.

Static checks: `check_app_integrity.py` OK (898 checks), `check_scope_traps.py`
OK, `check_api_paths.py` OK, `check_tracked_keys.py` OK,
`check_undefined_js.js` OK, `check_portal_handlers.js` OK,
`check_tag_balance.py` OK, `check_version_pins.py` OK.

`check_design_system.py` and `check_brand_spelling.py` **fail — and they fail
identically on a clean `origin/dev` checkout at `b202a37d`**, which I made and
ran to be sure. Neither touches a file this slice changed. See the report.

## Known gaps and shortcuts

* **The help text is under the input, not beside the tick** — *acceptable
  simplification*. Frappe renders a field's `description` as help text under
  the input on the Employee form, which is the one screen anybody fills this in
  on. The Positions tick dialog has no hint slot on a Positions row (only a
  "must fill in" row has one), so putting her sentence there would mean building
  a hint mechanism for one sentence. Flagged for her; one line of JS plus a
  words map would do it if she wants it.
* **No brand-new site was built** — *intentional trade-off*. Creating a site
  needs the MariaDB root password, which this session cannot read. Instead the
  fresh-install path is proved the way that can actually fail: the Property
  Setter is deleted, `lock_fields()` (the function `after_install` runs) is
  called, and the level is asserted back at 2 — with a prior assertion that the
  level really was 0 first, so the test cannot pass vacuously. Both tests were
  seen to fail with the `LEVEL_2` line removed.
* **DTC may ship this empty** — not debt, just a fact. Their workforce is
  largely shop-floor and may have no such numbers. The field is off on Positions
  until ticked, so an empty field shows nowhere.
* **`bench migrate` was not completed on the test site** — *intentional trade-off,
  and the one thing someone should repeat*. Two attempts both sat on
  `Command: Sleep`, waiting on a database lock. `test078`'s database is shared
  with the slice 079 bench, so forcing a migrate there is not mine to do. The
  field and its permlevel 2 were verified on both sites by running the two hook
  functions directly, which is what `migrate` and `install` call. **A clean
  `bench migrate` on a site nobody else is using would also unblock
  `test_joiner_079`.**

* **Subtract pass.** One thing removed:
  `test_alt080_creating_it_twice_writes_nothing_the_second_time` — it was
  testing Frappe's `create_custom_fields`, not this slice. Also considered and
  rejected as over-engineering: a second words map so the Positions tick dialog
  could carry her help text; a guard in `positions_profile` for a tenant that
  has `hrms` but not `alvoraa_portal` (no such configuration can reach the
  Positions page); a new CSS class for the `tel:` link (the mail link's class
  has no mail-specific styling, so it is reused).
