---
slice: 082-event-attendee-qr-form
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-13
status: waiting for Surbhi's approval - no product code written
youtrack: ALV-339
base: origin/dev c3885fad (worktree .claude/worktrees/082-event-form, branch slice/082-event-form)
---

# 082 · Event attendee QR form · Impact analysis and strategy

I recommend. Surbhi decides. Nothing below is built yet.

## 0. The answer first

**Bad news first.**

1. **AC-62 as written will fail, and it is the spec that is wrong, not CRM.** A stock Sales
   User **does** hold `export` (and `share`) on CRM Lead. What limits them is CRM's own row
   rule: they see only leads they own or are assigned. So their export holds only their own
   rows. AC-62 should say "S1's export holds only L1", not "refused". Proven on a fresh site
   (§1).
2. **Two small rules must be added to "what makes a form open" (§8.1), or a live event can
   fail with a server error.** CRM Lead requires `first_name` (and `status`, which CRM fills
   in itself). A form without a required field would make every save fail. And the form must
   be one of CRM's own (`module = "FCRM"`), the same test CRM itself uses. Both close the form
   cleanly instead.
3. **The OPS-27 alert only goes live after a release to `main`.** GitHub runs a scheduled
   workflow from `main`'s copy of the file. On `dev` it does nothing.
4. **Frappe's Error Log would copy attendee answers if the save crashed.** Frappe 16.35 logs
   an unexpected error with the local variables of the code (`get_traceback(with_context=True)`)
   and a snapshot of the request. The save must catch its own failures and log only the route
   hash and the error type (PRIV-6, OPS-28). Planned below.

**Verdict:** rung 4 (new code): one new module, one new page, three hooks, one patch, a
one-argument change to the slice 013 limiter, two new refusal codes. No new DocType, app,
job, queue, cache, npm or pip package, and **no change to `deploy/nginx.conf`**.

## 1. The three CRM facts, checked on a fresh site (OPS-23)

**Site.** My own stack, not the shared bench: containers `hrlocal-qr082`,
`hrlocal-qr082-db`, `hrlocal-qr082-redis` (image `alvoraa-app:dev-d3afcaa`: **Frappe v16.35.0,
CRM v1.84.0**, the image pins). New site `qr082.localhost`, then `install-app crm`. No dev or
production tenant touched. ERPNext, HRMS and our apps are **not yet installed** on it; the
full OPS-23 order (wizard, then CRM) is the first build step, because the door tests (AC-61
to AC-64) must run with our hooks present.

| # | Spec said | Checked | Result |
|---|---|---|---|
| F-1 | CRM Lead fields `first_name`, `mobile_no`, `email` `[UNVERIFIED]` | `get_meta("CRM Lead")` | **Confirmed.** `first_name` Data (**required**), `email` Data/Email, `mobile_no` Data/Phone. Also `last_name`, `phone`. Required fields: `first_name`, `status` |
| F-2 | Which published flag CRM uses `[UNVERIFIED]` | `crm/api/form.py` 454-459, 523-530; `crm/www/crm_form.py` 26 | **`crm_published`** (a Custom Field CRM puts on Web Form). CRM copies it onto Frappe's `published`. Our page reads `crm_published` |
| F-3 | Builder skips read-only fields; offers set-only-once `[UNVERIFIED]` | `_mappable_fields`, run on the site with our three test fields | **Confirmed both.** The picker skips `hidden` and `read_only` (so `custom_event_form` can never be put on a form; CRM's `save_form` also refuses it). It **offers** a `set_only_once` Check. Changing it after save is refused (`CannotChangeConstantError`) - O-3 closed, keep the property |
| O-2 | Does the builder emit layout rows? | `_seed_visible_fields`, `LAYOUT_BREAKS` | **Yes** - Section Break and Column Break rows. Our page draws them as nothing and accepts no value for them |
| O-4 | Does a guest insert need `ignore_mandatory`? | Insert as Guest with only `first_name`, `mobile_no`, two custom fields | **No**, provided `first_name` is on the form. `status` becomes "New" from CRM's own `validate_status`. One bypass only |
| O-5 | Does Frappe count a refused call in the window? | `frappe/rate_limiter.py` | **Yes, but it does not stretch the window.** It adds 1 before checking, and the window is fixed from the first call (the expiry is set once). Under option A a lockout ends at most 60 s after the window opened |
| AC-61 | Can a stock Sales User read every lead? | Three leads saved as Guest; L1 assigned to S1 | **No.** S1 lists only L1; S2 (another Sales User) lists none; Sales Manager lists all three; a login without a CRM role and Guest get a permission error. Rule: CRM's `permission_query_conditions` and `has_permission` (`crm/permissions/org_hierarchy.py`): owner = `lead_owner`, or a live assignment. **R3 does not trigger.** The full doors 1-6 test still runs in the build |
| O-9 | Is `request_guard.py` on the build base? | `origin/dev` `hooks.py` line 32, `request_guard.py` | **Yes.** It is the first `before_request` hook and drops `ignore_permissions` and `ignore_user_permissions` from every request. 01c §9 read a stale checkout. AC-60 proves it |
| - | Track changes | meta | **Already on** for CRM Lead and Web Form. No Property Setter needed (G-11, G-12 are rung 1) |
| - | Delete leaves copies | delete one edited lead | 1 Deleted Document row and 1 Version row remain. PRIV-5's hook is needed |

Other facts found on the way, which change the build:

- Frappe also serves its own stock page at `/<route>` for every published CRM form (CRM's own
  comment, `form.py` 456), plus CRM's `/crm-form/<route>`. Both stay as they ship (W3). Both
  use Frappe's `accept()`, limited to 10 a minute per address.
- CRM's `before_insert` enrichment (`enrich_form_submission`) runs only when
  `frappe.flags.in_web_form` is set. Our save does **not** set it, so it skips CRM's hidden
  defaults and its telemetry call. `status` still comes out as "New" from the controller.
  `[ASSUMPTION]` the organiser does not need a non-default status on event leads; the setup
  guide says so.
- PyQRCode and pypng are in the image. No new package.

## 2. Parallel-work check

**Incoming.** Worktree made from `origin/dev` `c3885fad` (13 Nov, ALV-337). The last week on
the files I touch: `hooks.py` gained ALV-337 (Employee Checkin `before_insert`) and ALV-338
lines; `tests/test_portal_security_010.py` gained ALV-318/319 tests (5 Nov). I build on top of
both; nothing of theirs is edited.

**Other work.** Every row on the work board (ALV-318, 281, 326, 328, 337) has **no commits
ahead of `origin/dev`** and no uncommitted change in my files. The shared main checkout
(`5aa654d2`, 446 behind) holds another session's uncommitted edits, including `hooks.py` and
`auth.py` (`MM`). Not mine; untouched; I never build there. A stopped container named
`hrlocal-082` (4 Nov, slice 082-joiner-to-employee) is someone else's; left alone, which is why
mine are named `hrlocal-qr082*`. **Question for you:** is anyone outside these sessions
working in `hooks.py`, `field_app_limits.py` or `worker-health.yml`?

| File | Hot? | Change | Who else | Plan |
|---|---|---|---|---|
| `alvoraa_portal/event_form.py` | new | the save, the open check, the three hooks | - | - |
| `alvoraa_portal/www/event-form.html`, `www/event_form.py` | new | the page | - | - |
| `alvoraa_portal/hooks.py` | **hot** | 1 route rule; `Custom DocPerm` validate; `CRM Lead` `after_delete` added next to 057's `on_update`; `after_app_install` becomes a 2-item list | ALV-337/338 landed today | Append only, rebase just before commit, read the diff |
| `alvoraa_portal/patches.txt` + `patches/v1_0/event_form_fields.py` | **hot** | one line at the end | - | Append; rebase before commit |
| `alvoraa_portal/field_app_limits.py` | shared (slice 013) | `_limited(..., window=WINDOW_SECONDS)` | - | Default unchanged |
| `alvoraa_portal/field_app_errors.py` | shared | add `FIELD_INVALID` (422, label) and `FORM_CLOSED` (404) | - | Added, never renamed (its own rule) |
| `tests/test_portal_security_010.py` | **hot** | one CEILINGS row | ALV-318 row landed | One line |
| `tests/test_event_form_082.py` | new | the slice's tests and pins | - | - |
| `.github/workflows/worker-health.yml`, `scripts/check_event_refusals.sh` | workflow | OPS-27 step | - | Own step; the worker check untouched |
| `scripts/check_guest_rows.sh` | new | OPS-30 read-only check | - | - |
| `docs/slices/082-.../setup-guide.md` | new | AC-45 | - | - |

**Pin tests that keep existing work alive:** `test_field_app_step6_013` (reads every
`__alvoraa_limit__`), `test_employee_documents_078`, `test_joiner_078`, `test_notices_076`
(each unpacks the 4-part tuple, last part the window - unchanged shape); the 057 tests for
`crm_steps.on_status_change` / `on_app_install`. **New pin:** `test_event_form_082` reads
`save.__alvoraa_limit__ == ("event_form_key", "route", 300, 60)`, the route rule, the three
hook entries and the two codes, so a bad merge that drops any of them fails CI.

## 3. Cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | Yes | the files above |
| `crm` | **Read only.** Never edited | Our page reads its Web Form record; the save inserts a CRM Lead through CRM's own controller (all its validation runs) |
| `frappe` | Config only | Custom Fields; a validate hook on `Custom DocPerm` |
| `hrms`, `erpnext` | **No code, no data.** | HRMS Web Forms (job application) are refused by the `module = "FCRM"` and `doc_type = "CRM Lead"` rules (AC-21). The `Custom DocPerm` hook also stops a Guest row on `Employee` - a door closed, nothing opened. No leave, attendance, payroll, appraisal or org data touched |
| `alvoraa_goals`, `alvox_compensation` | No | - |
| slice 057 (`crm_steps`) | Shares CRM Lead | `on_status_change` and `refresh_task_labels` run on each event-lead insert. Both do nothing unless `custom_lead_type` is set (E-16; guide forbids it on event forms). `after_app_install` keeps 057's entry and adds ours |
| slice 013 (`field_app_limits`) | One argument | see §4 |

### Every caller of what I change

- `field_app_limits._limited`: **31 decorator uses in 16 files** - `employee_documents_read`
  (1), `employee_photo` (2), `expense_evidence` (2), `field_app_device` (2), `field_app_join`
  (8), `field_app_records` (1), `field_checkin` (2), `joiner_invite` (2), `joiner_public` (4),
  `joiner_to_employee` (2), `my_profile` (1), `notices` (1), `positions_profile` (1), plus
  tests. None passes `window`, so all keep 3,600 s. `_seconds_left` already takes a window;
  the wrapper passes its own instead of the module constant. `_limited_by_address`: untouched.
- `field_app_errors.CODES`: read by `refuse()` and `field_app_housekeeping` counters and by
  its own table test. Two new keys; nothing renamed.
- `hooks.after_app_install`: today a string naming `crm_steps.on_app_install`; becomes a list
  holding that and `event_form.on_app_install`.
- Nothing else existing is changed.

## 4. The approach

**One new module `event_form.py`**, used by two callers (the page and the save), so the open
check lives once:

1. `form_state(route) -> (web_form | None, problem | None)` - the §8.1 rules, read through the
   ORM (`frappe.get_all("Web Form", filters={"route": route}, ...)` then one `get_doc`).
   Rules: exists; `doc_type = "CRM Lead"`; **`module = "FCRM"` (new)**; `crm_published = 1`;
   `login_required = 0`; every non-layout row's type is on the allowed list; no PRIV-2 word
   ("pan" whole word only, pending O-6); both consent fields present and the "I agree" row has
   a notice; no row whose CRM Lead field is hidden; **every required CRM Lead field except
   `status` and `naming_series` is on the form (new)**.
2. `save(route: str, values: str) -> dict` - `@frappe.whitelist(allow_guest=True,
   methods=["POST"])`, `@_limited("event_form_key", "route", limit=300, window=60)` (R1 = A).
   Re-runs `form_state`; refuses unknown keys (400); validates each value (422, label only);
   sets `custom_event_form`; one `insert(ignore_permissions=True)` - **the only bypass**,
   CEILINGS row at 1. Answers one fixed body. Every refusal writes one `frappe.logger
   ("event_form")` line: time, route hash, reason. Any unexpected error is caught, logged with
   `frappe.log_error(title, message=<route hash + error type>)` - passing the message stops
   Frappe adding local variables - and answered `SERVER_ERROR`.
3. `refuse_guest_perm(doc, method)` - `Custom DocPerm` validate: refuse role `Guest` with
   `read` or `select` on `User`, `Employee`, `CRM Lead` (SEC-6). Catches CRM's
   `grant_guest_link_access`, which saves through the same doctype.
4. `after_lead_delete(doc, method)` - `CRM Lead` `after_delete`, only when
   `doc.custom_event_form` is set: removes its Deleted Document, Version and Comment rows
   (`frappe.db.delete` with a name filter - a system clean-up after a permitted delete, not a
   user-callable path; listed here and in `03`). Writes one log line: lead name, user, time,
   form - no personal data (spec §16's recommendation).
5. `ensure_fields()` - `create_custom_fields` for the five fields; called from a patch guarded
   on `frappe.db.exists("DocType", "CRM Lead")` and from `on_app_install("crm")`. **Never a
   fixture.**

**The page** `www/event-form.html` + `www/event_form.py`, rule
`{"from_route": "/event-form/<route>", "to_route": "event-form"}`. `no_cache = 1`. Plain HTML,
the phone's own fonts, no images, one small inline script for the client check, Send and the
§6.2 messages. The organiser box is rendered only when the session user holds Sales Manager or
System Manager. The QR is drawn on the server with PyQRCode from `get_url()` + route, inline
SVG, inside that box only; the card is turned into a PNG in the browser.

**OPS-27 alert:** a new step in `worker-health.yml` that runs
`scripts/check_event_refusals.sh` against both stacks: read-only `grep` of each site's
`event_form` log for the last 60 minutes, fail at 30 or more `limit` + `closed` refusals for one
route hash (AC-73). 30 is 10 % of a 300-person hall; it is a number for you to change.

### Rungs rejected

| Rung | Why not |
|---|---|
| 1 Already there (`/crm-form/<route>`) | Refuses ~250 of 300 saves from one Wi-Fi (10 a minute per address); 14 px inputs; Google Fonts (OPS-12/13) |
| 2 Configuration | Frappe and CRM have no setting for an event-keyed limit, a stamp, or Guest-row refusal |
| 3 Customisation (Client/Server Script, Property Setter) | A script cannot change the rate limit on `accept()`, nor the page layout CRM renders; a Server Script on `Custom DocPerm` is site data, not shipped code, and is not tested in CI |
| 5 New DocType (an "Event") | The Web Form record already is the event (spec §3) |

**Main trade-off:** our own page and save copy a little of what CRM's page does, and read
CRM's Web Form record. A CRM upgrade that renames `crm_published` or the row fields breaks the
page. OPS-33's test (AC-11) turns that into a red CI run rather than a silent failure. The
cheaper path (CRM's page) cannot survive a full hall.

## 5. Copy for the missing-notice box (P-3, written in 01b's style)

> **This form cannot open for attendees yet.** The "I agree" question is missing, or has no
> notice under it. Add the "Consent: this event" and "News OK" questions in CRM, and write the
> notice in the description of "I agree". Then open this page again. Until then attendees see
> "This form is not taking answers".

And for the new required-field rule, same shape:

> **This form cannot open for attendees yet.** It has no "First name" question, and CRM needs
> one to save a lead. Add it in CRM, then open this page again. Until then attendees see "This
> form is not taking answers".

Sensitive-word case: AC-36's wording with the label and the bracket "(it looks like it asks
for sensitive personal data)". All English; translatable; no Hindi (staff-only box).

## 6. Personas

| Persona | What changes |
|---|---|
| **Attendee (Guest)** | Can open `/event-form/<route>` for a clean published CRM form and save one lead. Reads nothing back |
| **Employee only** (HR Manager / Employee slot at a DTC-style tenant) | **Nothing.** No CRM role, no CRM Lead rows (proven: permission error) |
| **Sales User** | Sees only owned or assigned event leads (proven). Export holds only those |
| **Sales Manager** (HR Manager slot for this slice) | Sees the organiser box and the QR; reads and deletes event leads; can no longer publish staff names with CRM's Guest grant button |
| **System Manager** | Same, plus creates question fields; cannot add a Guest read/select row on User, Employee or CRM Lead |
| **CXO** | Only through the roles they hold (R5) |

## 7. Seven dimensions (proposal)

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **Neutral** | Staff paths: one `if` in a CRM Lead `after_delete`, one validate on the rare Custom DocPerm save. Save: ~2 Redis calls + 2 reads + CRM's insert (~15-25 queries, estimate) - to be measured (AC-8, AC-28). No cache, no job |
| Security | **Degrades, by design and bounded** | A new public write door. Bounded by: allow-list of keys, one counted bypass, 300/60 s per event, nginx's 120/min per address, the open check on GET and POST. **Improves** elsewhere: the `Custom DocPerm` hook closes the staff-name leak that exists today on any tenant with CRM |
| Reliability | **Improves** for event capture | Synchronous save; every failure keeps the answers; crashes caught and answered plainly |
| Scalability | **Degrades slightly** | An event burst uses the shared web workers (production: 4 x 2 threads for all tenants). Capped at 300 saves a minute per event; OPS-32 measures it |
| Maintainability | **Degrades slightly** | New code reads another app's record; pinned by AC-11. One module, no abstraction |
| Data integrity | **Neutral** | One insert per save, one transaction; a lost reply can make a duplicate (E-1, accepted). No denormalised data |
| Compliance / privacy | **Improves on staff data, adds public data with controls** | New personal data from the public (consent, notice, erasure hook, no logs). The SEC-6 hook removes an existing exposure |

## 8. How each requirement is met

| Item | How |
|---|---|
| SEC-1 | Writable keys = the open form's non-layout, non-hidden rows; any other key → 400 |
| SEC-2 | One fixed success body; failures carry only the code (+ label for `FIELD_INVALID`) |
| SEC-3 | One `ignore_permissions` in `event_form.py`, CEILINGS = 1; no Guest DocPerm added |
| SEC-4 | `form_state` on GET and POST; allowed list; one closed card for every reason |
| SEC-5 | **Not adopted** (your R1 = A). OPS-19/20 numbers used |
| SEC-6 | `Custom DocPerm` validate hook; OPS-30 script for existing rows (read only) |
| SEC-7 / OPS-15 | Box rendered on the server by role; `no_cache` |
| SEC-8 / OPS-7 | `get_url()` only; no host or site parameter read |
| SEC-9 | Length caps; stored as typed; editor types refused; browser test |
| SEC-10 | CRM's own row rule (proven); door tests in the build |
| PRIV-1, -2, -3 | Guide default; sensitive-word rule; consent required on the server, unticked by default, ignores URL and Web Form defaults; track changes already on |
| PRIV-4 | Untick "News OK"; CRM Lead Version (already on) |
| PRIV-5 | `after_delete` hook (§4.4) |
| PRIV-6 / OPS-28 | No external host; body-only POST; caught errors logged without values; hashed limiter key |
| OPS-5, -6, -8, -10, -12, -13, -14, -17, -18, -21, -22, -29, -33 | Built as listed in the spec's traceability; no nginx, secrets or compose change |
| OPS-19 / OPS-20 | `window` argument; 429 and 503 both shown as "too many" |
| OPS-23 | Site started (§1); full order next |
| OPS-24 | Listed in `03` from the full site: today CRM's `before_validate` SLA lookup, Frappe's global `on_update` (assignment rules, search index), 057's two hooks |
| OPS-25 | Nothing to build; R10 open |
| OPS-26 | One log line per refusal |
| OPS-27 | AC-73 (added to the spec today) |
| OPS-30 | `scripts/check_guest_rows.sh`, proven to print FAIL on a planted row |
| OPS-31, OPS-32 | Measured locally, then on dev only on your word (R2) |
| OPS-2, -3, -4, -9, -11, -16 | Not adopted / folded into the gates above, per the approved brief |

## 9. Data doors

| Persona | Frappe rule that limits them | Doors |
|---|---|---|
| Guest | No DocPerm on CRM Lead or Web Form; `Custom DocPerm` hook stops one being added | 1-6 → 403 |
| Employee only | No DocPerm on CRM Lead | 1-6 → 403 |
| Sales User | CRM `permission_query_conditions` + `has_permission` (owner or assignee) | own/assigned only |
| Sales Manager | DocPerm, all rows | all |

**Bypasses added: 2, both listed.** (1) the guest insert, `ignore_permissions=True`, counted in
`TestSec16IgnorePermissionsCeiling.CEILINGS[("alvoraa_portal", "event_form.py")] = 1`;
(2) the `frappe.db.delete` clean-up in `after_lead_delete`, which runs only after a user with
delete right has deleted the lead and takes no user input. The CEILINGS gate counts only the
word `ignore_permissions`, so (2) is recorded here and in `03`, not in the gate. I did not test
yet: doors 7-10 (no `hrms`/`erpnext` method takes a CRM Lead; Data Import of CRM Lead is a
Sales Manager action).

## 10. Consequences nobody asked about yet

- **Custom Fields on sites without CRM:** the patch checks for CRM Lead and does nothing;
  `after_app_install` adds the fields when CRM arrives later. A fixture would break `migrate`
  on every tenant without CRM - not used.
- **The `Custom DocPerm` hook runs on every tenant**, CRM or not. On a tenant that already has a
  Guest read row on User, Employee or CRM Lead, the **next save of that row** fails. Our own
  permission code never writes Guest rows (checked: `baseline`, `module_access`,
  `employee_field_rights`, `people_settings`, `permission_health`). Run OPS-30's count before
  the release so you know if any tenant has one (R4).
- **Rollback:** revert the code. The fields stay (empty columns harm nothing). Leads stay.
- **No caching** anywhere; nothing to invalidate.
- **A form edited mid-event:** a question removed between GET and POST makes the attendee's
  extra key unknown → 400 → "Not sent". Rare; the guide says do not edit a live form.
- **Scheduler, queues:** unchanged. The OPS-27 step runs on the existing hourly runner.

## 11. Disagreements with the spec and DevOps inputs

1. **AC-62:** Sales User has export; the test should assert S1's export holds only L1.
2. **§8.1:** add `module = "FCRM"` and "all required CRM Lead fields on the form" (§4.1).
3. **§6.3:** the flag is `crm_published` (CRM's own), not `published`.
4. **§6.1 / G-11, G-12:** no Property Setter - track changes is already on for both.
5. **OPS-27 / 07:** the alert reaches you only after a release to `main`; on `dev` it is
   inert. Threshold 30 is mine, yours to change.
6. None with the R1 = A limiter numbers.

## 12. Subtract pass (on this proposal)

Removed: the track-changes Property Setter (already on); a separate `www` helper module (the
open check lives in `event_form.py`, used by both callers); an app-level address limit (R1 = A);
applying CRM's hidden defaults (CRM's controller already sets `status`). Kept though cuttable:
the erasure log line (without it nothing records who erased a lead).
