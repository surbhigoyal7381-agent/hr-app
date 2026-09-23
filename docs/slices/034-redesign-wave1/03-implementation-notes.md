---
slice: 034-redesign-wave1
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-23
status: stretches 1 and 2 of the build complete — local only, not pushed, not merged
covers: the new-file work, plus W1D-21/SEC-16 (the staff list and its switch, SERVER SIDE ONLY). US-10 (the page split) and SEC-13 (the Team query) are NOT started
base: slice/034-redesign-wave1, rebased onto origin/dev (2a0ea60)
commits: stretch 1 — 9842367, a6d59c4, 8e243aa, a0fc8cb, 1df6c77 (after the rebase); stretch 2 — see the second half of this file
---

# Wave 1 — what was built in the first stretch

## 1. Why this is only part of the slice

Two files are held by slice 035, which has uncommitted changes in both:

- `alvoraa_portal/alvoraa_portal/www/hrms-employee.html`
- `alvoraa_portal/alvoraa_portal/hr_api.py`

Checked, not assumed, before any edit: `git status` in
`.claude/worktrees/035-wrong-numbers` shows both modified, plus `goals_api.py` and
`performance_api.py`, which were therefore avoided too.

So **US-10 (the page split) and SEC-13 / AC-72 (the Team query rebuild) could not
start**, and everything downstream of the split — the frame includes, the rail, the top
bar, the routes, the sheets, the five states — is not built. The work below is the part
that lives in new files, plus one addition to `access.py`, which nobody else holds
(slice 030 owned it and is cleared, worktree clean).

Nothing was worked around. Neither held file was read into a new file, copied, or
re-created.

## 2. What was built, file by file

| File | New? | Mechanism | Why |
|---|---|---|---|
| `hrms/hrms/alvoraa_hr_core/access.py` | extended | **Extend** — one new function, and `permitted_employees` rebuilt on it | SEC-4 asks for one definition, not a copy. Two shapes of one rule |
| `alvoraa_portal/alvoraa_portal/frame_api.py` | **new** | **Build** | SEC-12's fixed key list is the reason it is a new endpoint and not a bigger old one |
| `alvoraa_portal/alvoraa_portal/www/hrms_employee_next.py` | **new** | **Build**, copying `alvoraa_admin.py`'s shape | The two-lock pattern already exists in this repo and already learned its lesson |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee-next.html` | **new** | **Build**, deliberately almost empty | The frame it will host comes from the blocked page split |
| `scripts/check_preview_flag.py` | **new** | **Build**, alongside the existing `scripts/check_*.py` family | A bench test of this rule skips when the app is mounted, and a skipped check protects nobody |
| 4 test files | **new** | — | Each endpoint's Guest, wrong-persona and scope cases ship in its own commit (SEC-2 / M2) |

### `permitted_employee_filters` (SEC-4, AC-73) — commit `3e3b895`

`permitted_employees()` is now `frappe.get_all("Employee", filters=permitted_employee_filters(user), pluck="name")`.
Behaviour is byte-identical for every caller: System Manager gets everyone, HR gets their
companies, store HR gets their branches, everybody else gets nothing, and **every status
is still returned**, so a leaver's records still belong to the store that had them.

The one thing worth reading twice is the refusal. In Frappe an empty filter dict means
*no conditions*, which means *every record*. A filter-shaped twin that copied
`permitted_employees()`' "return nothing" instinct would `return {}` and hand a plain
employee the whole company. So:

- refusal is `{"name": ["in", []]}` — a real condition that matches nothing
- "everyone" is `{"name": ["!=", ""]}` — also a real condition, never `{}`
- both are module constants, and the helper returns **copies**, so one caller cannot
  mutate the next caller's answer

`"!="` was chosen over `["is", "set"]` because it needed no guess about operator support.

### `get_frame` (SEC-12, AC-46, AC-8, US-2, US-17) — commit `328d5a0`

One call in place of `get_portal_context` + `get_available_features` + `get_switch_target`,
which it calls on the server so the answers cannot disagree with the old ones.

**The payload is filtered through a constant `FRAME_KEYS` tuple on the way out.** Adding a
field inside the function is not enough to ship it — there is a test for exactly that.
The caller's own block is six fields. `date_of_birth`, `gender`, `cell_number`,
`date_of_joining`, `reports_to` and `branch` are checked for at **every depth** of the
serialised payload, per persona.

Two exclusions made deliberately, beyond what SEC-12 lists:

- **`manager_name`** (which `get_portal_context` returns) is not carried. It is another
  person's name in every payload, the frame does not need it, and §6 already removed
  "your manager" from the empty-search wording. PRIV-7 says the frame widens nothing.
- **`roles`** is not carried. Four booleans instead.

Persona rules 1–6 are implemented as §2 writes them, with the correction that matters:
**rules 1 to 5 are tried only for somebody with an Active Employee record.** Asha and the
leaver both reach rule 6 and are offered no Time, Pay, Growth or Team.

`has_reports` is its own count query. It is *not* today's `is_manager`, which is also true
for any HR user when anybody in the tenant has no manager.

`may_save_settings` (AC-67) mirrors `hr_api._require_hr` + `_refuse_store_hr`. It is
computed rather than delegated, because `_refuse_store_hr` writes a security-log refusal
and a store HR person opening the portal is not a refusal worth recording. **The drift
risk is covered by calling the real `set_org_setting` endpoint for every persona and
asserting it refuses exactly when the flag is false.**

### The preview page (SEC-1, AC-40, AC-74, AC-65) — commit `1fb9727`

Lock 1 is the site flag, read **before** the login check and before the role check:
`portal_preview` absent or `0` → `frappe.DoesNotExistError` → **404 for everyone,
System Manager included**. Lock 2 is System Manager only → `frappe.PermissionError` → 403;
Guest → redirect to login.

Status codes verified against `frappe/exceptions.py` in the installed Frappe 16.33.1:
`DoesNotExistError.http_status_code == 404`, `PermissionError.http_status_code == 403`.

`no_cache = 1` and `sitemap = 0` are module attributes, which is how Frappe reads them
(`website/page_renderers/template_page.py:22`), plus `no-sitemap` and `noindex` in the
template.

## 3. Acceptance checks

| AC | Status | How |
|---|---|---|
| AC-46 (SEC-12) | **met** | `FRAME_KEYS` filter + per-persona deep scan for the six banned fields |
| AC-8 | **met** | Asserted equal to all three old calls, per persona |
| AC-9c | **met** | `review_open_count` equals `_with_review_count`'s value for HR, `None` otherwise |
| AC-10, AC-47, AC-63, AC-68 | **met** | Persona rules 1–6; Asha and the leaver reach rule 6 |
| AC-11 | **met** | All five named bar cases asserted exactly |
| AC-67 (W1D-03) | **met, server side** | Flag pinned against the real endpoint. **The panel itself is in the held page — not built** |
| AC-73 (SEC-4) | **met** | Direct "never `{}`" assertion, three non-HR callers, zero rows |
| AC-75 (W1D-19) | **met** | All four cases, labels asserted word for word |
| AC-69 (SEC-2) | **met** | Registry test; a whitelisted function with no entry fails |
| AC-70 (SEC-15) | **met** | No `global`, no module-level dict/list/set |
| AC-71 (SEC-6) | **met** | No `ignore_permissions`, checked on code with prose stripped out |
| AC-40, AC-74, AC-65 (SEC-1) | **met, and confirmed over real HTTP** | See §6 |
| AC-7, AC-13–AC-19, AC-30–AC-42, AC-48, AC-60–AC-62, AC-64, AC-66 | **not started** | Client side, behind the page split |
| AC-72 (SEC-13), AC-76 (SEC-16), AC-43, AC-20–AC-29, AC-49–AC-52 | **not started** | Held files, or `inbox_api` / the staff list |

## 4. The seven non-functional dimensions, against the code actually written

| Dimension | Verdict | One line |
|---|---|---|
| Performance | **improves** | Three start-up round trips become one. `get_frame` adds two small reads — one `Employee` row by `user_id`+status, one `COUNT` on `reports_to` (both indexed columns) — and no query runs in a loop |
| Security | **improves** | A fail-open filter shape is closed before anything uses it; the new endpoint refuses Guest and takes no caller-supplied doctype, field or name; the preview page's first lock is the site, not the role |
| Reliability | **neutral** | No new external call, no new background job. The preview page's two locks throw rather than degrade, which is the intended end state |
| Scalability | **neutral** | Nothing here grows with headcount. `permitted_employees()` still reads every permitted name into Python — unchanged, and the new filter shape is what lets later screens stop doing that |
| Maintainability | **improves** | One scope rule in two shapes instead of two rules; the persona table is one tuple of tuples that reads like §2; a registry test makes the next endpoint's tests non-optional |
| Data integrity | **neutral** | Nothing is written. `get_frame` reads `get_portal_context`'s existing per-user cache for menu shaping only, never for what an endpoint returns |
| Compliance / privacy | **improves** | Six fields instead of the whole Employee record and the whole role list. `manager_name` dropped as well. No personal data in any log line added here — none were added |

## 5. NFR notes

- **Query count for `get_frame`:** the three existing calls' queries, plus 2 (own Employee
  row; `COUNT` on `reports_to`), plus 1 for `User.full_name`, plus 1 for
  `permitted_branches` only when the caller is an HR Manager who is not a System Manager.
- **Indexes:** none added. `Employee.user_id`, `Employee.status` and `Employee.reports_to`
  are existing columns already filtered on elsewhere.
- **Background jobs:** none.
- **Permission enforcement points:** `get_frame` (Guest refused by decorator and by an
  explicit line); `hrms_employee_next.get_context` (site flag, then login, then role);
  `permitted_employee_filters` (fails closed).
- **Sensitive fields touched:** the six in `ME_FIELDS` — name, job title, department,
  photo, company — all the caller's own. The six banned fields are tested for absence.
- **Fallbacks:** the bottom bar shortens rather than offering a button that refuses.

## 6. What the tests actually said

Run on **my own container**, not the shared bench: `hrlocal-034` (mounts this worktree),
own redis `hrlocal-034-redis`, own sites volume `hrlocal-034-sites`, own site `test034`
(own database on `hrlocal-mariadb`). `hrlocal-bench` and `test_site` were not used for any
run. The only thing done against `hrlocal-bench` was reading Frappe's own source files to
verify APIs.

| Module | Result |
|---|---|
| `test_frame_api_034` | **33 passed** |
| `test_frame_endpoint_registry_034` | **7 passed** |
| `test_permitted_employee_filters_034` | **10 passed** |
| `test_preview_page_034` | **12 passed, 2 skipped** |
| `test_store_hr_scoping_030` | 14 passed |
| `test_branch_scope` | 11 passed |
| `test_attendance_scope_012` | 13 passed |
| `test_portal_security_010` | 5 passed (incl. the `ignore_permissions` ceiling) |
| `test_module_access` | 51 passed |
| `test_portal_call_paths` | 7 passed |
| `scripts/check_app_integrity.py` | 623 checks, OK — run before every commit |
| `scripts/check_preview_flag.py` | 11 files checked, OK |

**Fail-without-the-fix, proven not claimed.** Making `permitted_employee_filters` return
`{}` for the refusal case turned 3 of the 10 filter tests red. Worth recording *which*
test did not turn red: `test_the_two_shapes_agree_for_every_persona` still passed, because
`permitted_employees()` is built on the same broken helper and the two agreed — wrongly,
together. The direct "never `{}`" assertion is the one that caught it, which is exactly
why AC-73 asks for that assertion rather than for an empty result.

**Two things the first run got wrong, and what they cost.**

1. **Five bottom-bar tests failed** because the review fixtures this file inherits patch
   `subscription.has_feature` to return `True` for everything. Every `_sell()` was silently
   ignored. Fixed by stopping that patch in `setUp` and restarting it in `tearDown`, plus a
   guard test that fails if the patch is ever on again — otherwise every feature test in
   the file would be meaningless while looking green.
2. **`check_preview_flag.py` passed a deliberately broken production file** on its first
   version, because `production.env.example` contains "example" and "example" was in the
   allow-list. That file is the template somebody copies to make the real production env,
   so the flag would have reached production by the shortest route available. Marker list
   cut to `dev` and `test`; all four cases now proven.

**Checked over real HTTP as well.** `bench serve` on my own site, real sessions, real
status codes — because AC-40 and AC-74 are written as HTTP checks and an exception class
is not an HTTP response.

| | Guest | System Manager | HR Manager | Employee |
|---|---|---|---|---|
| `portal_preview: 1` | **301** to login | **200** | **403** | **403** |
| flag absent | **404** | **404** | **404** | **404** |

Two sanity checks ran in the same breath, so the 404 row cannot be a broken server or a
dropped session: `/hrms-employee` still returned **200** for the same cookie, and
`frappe.auth.get_logged_user` still named the System Manager. The 404 is the page not
existing, not the person being refused.

**Worth recording, because it nearly produced a false pass.** The first flag-off run
reported 200 for the System Manager. The flag had not actually been removed: my `pkill`
pattern matched its own shell and killed the command before the edit ran. Frappe also
caches site config per request, so a genuine flag change needs the server restarted. Both
are test-harness facts, not defects — but a 200 read as "the lock failed", or the earlier
green read as "the lock held", would both have been wrong.

## 7. What else moved while I worked

Rebased onto `origin/dev` at the start: **9 commits came in, all slice 013 (mobile field
app)**. In my areas they touch only `field_app_notice.py` and `test_field_app_step1_013.py`
— nowhere near the frame, the scope helpers or the www pages. The rebase was clean, no
conflicts, nothing to reconcile. A second `git fetch` before committing showed no further
movement.

## 8. Known gaps and shortcuts

- **The whole client side is missing** — *not a shortcut, a blocked dependency*. The frame
  has a server but no frame. Nothing calls `get_frame` yet.
- **The preview page is nearly empty** — *acceptable simplification*, forced by the same
  block. It exercises the locks, which is the part SEC-1 is about.
- **The `deploy/` test skips on a mounted bench** — *intentional trade-off*, and the reason
  `scripts/check_preview_flag.py` exists. The script should be wired into CI next to
  `check_app_integrity.py`; until it is, it only runs when somebody runs it.
- **`ALLOWED_ORG_SETTINGS` / `_require_hr` mismatch, noticed and not touched** — *flagged,
  not fixed*. AC-67 says an **HR User** sees Org settings read-only, but
  `hr_api.get_org_setting` requires HR Manager or System Manager, so an HR User cannot read
  them at all today. That is in a held file and is a spec-versus-code disagreement, not a
  typo. **It needs a decision before the Org settings panel is built.**
- **Open question 6 is still open** (a tenant System Manager's Team screen becoming the
  whole tenant). It does not block anything here; it blocks the SEC-13 commit.
- **`driver-portal.html` includes `design_system.html` four times** — noticed while looking
  for a page pattern. Not my slice, not touched, recorded so somebody can pick it up.

Nothing in these commits was left in that the task did not need: no feature flag, no
speculative abstraction, no scaffolding for a later wave.

---

# Wave 1 — the second stretch: the staff list and its own switch (W1D-21, SEC-16, AC-76)

**Local only. Not pushed, not merged into `dev`, nothing run on a server.** Built and
tested in my own container `hrlocal-034` on site `test034`. The shared bench
`hrlocal-bench` was only **read** (to check Frappe's own source for `get_all`'s paging
arguments and `db.count`); no bench command was run against it.

## 1. What came in from `origin/dev` before I started

Rebased `slice/034-redesign-wave1` onto `origin/dev` **`2a0ea60`** (it was on `da2193d`).
Clean, no conflicts. **Ten commits came in:**

| What came in | Files | Does it touch mine? |
|---|---|---|
| Slice 013 step 6 — the field app's daily clean-up, daily counts, "what does the app hold about me?", the app-version floor and its CI check | `field_app_housekeeping.py`, `field_app_records.py`, `field_app_alerts.py`, `field_app_errors.py`, `field_checkin.py`, `hooks.py`, a new `Alvoraa Field App Daily Count` doctype, three test files, `scripts/check_min_app_version.py`, `mobile/field-app/releases.json` | no |
| **`subscription.py` — three lines**: `Alvoraa Field App Daily Count` added to `TENANT_DOCTYPES` | `subscription.py` | **yes, same file** — but a different list, nowhere near `FEATURES`. No conflict, and my key sits on its own |
| Slice 036 — gzip in nginx, and a device rate-limit zone for the phone app | `deploy/nginx.conf`, `scripts/check_nginx_conf.py`, `scripts/check_nginx_forwarded.sh`, `.github/workflows/*` | no |
| Deploy: `premigrate_rename` runs per site | `.github/workflows/deploy.yml` | no |

I read the incoming `subscription.py` diff line by line before editing that file, because
it is the one overlap. Nothing of theirs was moved, re-indented or lost.

## 2. What was built, file by file

| File | New? | Mechanism | Why |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/subscription.py` | extended | **Configure** — one new `opt_in` key, `staff_list`, in the existing `FEATURES` registry | SEC-16 says reuse, not a parallel mechanism. `get_available_features` already loops the registry and publishes `plan_<key>`, so the flag reaches the page with no new call and no new pattern |
| `alvoraa_portal/alvoraa_portal/staff_api.py` | **new** | **Build** | There was no staff-list endpoint. It is a new file rather than a line in `hr_api.py` partly because `hr_api.py` is held by slice 035, and partly because SEC-2's registry test covers whole files — a new file joins it by one line in `MODULES` |
| `alvoraa_portal/alvoraa_portal/frame_api.py` | extended | **comment only, no behaviour change** | See §4. The staff list deliberately does **not** open the Company group |
| `alvoraa_portal/alvoraa_portal/tests/test_frame_endpoint_registry_034.py` | extended | **Extend** | `staff_api.py` added to `MODULES`, and one registry row naming its three cases (SEC-2/AC-69) |
| `alvoraa_portal/alvoraa_portal/tests/test_opt_in_features.py` | extended | **Extend** | `SHIPPED_OPT_IN` is a deliberate pin: adding an opt-in key must be named there or four tests fail. They did fail; that is the mechanism working |
| `alvoraa_portal/alvoraa_portal/tests/test_staff_list_034.py` | **new** | **Build** | 28 tests |

### The key, and where the reasoning is written down

The decision — org chart stays paid on `plan_org_structure`, staff list gets its own
switch, commercial question deliberately left open — is written **in `subscription.py`
beside the key**, not only in a document, because that is where the next person will be
when they are tempted to "fix" a tenant that cannot see the screen by adding it to a plan
bundle. The comment says not to, and says to tick it for that tenant instead. The same
reason is repeated in `test_opt_in_features.py`'s `SHIPPED_OPT_IN` list and at the top of
`staff_api.py`.

### The endpoint

`staff_api.get_staff_list(q=None, start=0, limit=12)` returns
`{"rows": [...], "total": n, "start": n, "limit": n}`.

Three gates, in this order, all before any read:

1. **Guest** — refused, belt as well as the missing `allow_guest`.
2. **The feature switch**, read with `subscription.has_feature` — the same function the
   `requires_feature` decorator calls. The decorator itself is **not** used, for one
   reason: it does not log the refusal, and abuse case A14 is precisely about somebody
   calling this endpoint by hand on a tenant that does not have it. The refusal goes
   through `access.refuse`, which writes one structured line and throws.
3. **The scope**, from `access.permitted_employee_filters()`. A caller whose filters come
   back as the `NO_EMPLOYEES` sentinel is refused outright rather than handed an empty
   list — an empty list reads as "this company has no staff".

Then `status = "Active"` is added by this caller (the shared helper returns every status
on purpose), the search term is escaped for `%` and `_`, and the caps are applied.

**The refusal is the same sentence in every case** — section 6's
*"This page is not part of your access. Ask HR if you think it should be."* A plain
employee must not be able to tell "your company did not buy this" from "you are not HR".

## 3. The acceptance checks

| AC-76 case | How it is met | Test |
|---|---|---|
| Key on, HR caller, searchable list of name, job title, department, photo | `get_staff_list` returns PRIV-2's five keys | `test_the_payload_holds_exactly_the_five_keys`, `test_a_search_finds_a_name_inside_the_scope_and_never_outside_it` |
| Store A's HR, key on → store A only; a head-office name is not found | `permitted_employee_filters()`; an employee with no branch is outside every store | `test_store_hr_gets_their_store_and_nobody_else`, and the head-office half of the search test (A15) |
| Key on, `plan_org_structure` off → staff list works, no org-chart entry | Two independent keys | `test_the_org_chart_is_untouched_and_the_two_are_independent` |
| Key off, `plan_org_structure` on → no staff-list entry, typed address shows the no-permission line | **Server half done, browser half NOT wired** — see §5 | `test_hr_is_refused_on_a_tenant_that_was_never_given_the_feature` |
| Key off, HR calls the endpoint by hand → refused on the server (A14) | Gate 2 above | same test, plus `test_the_refusal_carries_no_personal_content` |
| Key off, HR with no reports still has the Team screen | Untouched by this stretch; it is SEC-13, still not started | — |
| The key is in no plan bundle and in `OPT_IN` | Registry | `test_it_is_in_no_plan_bundle`, `test_a_site_with_nothing_recorded_does_not_get_it`, and `test_opt_in_features`'s four pins |
| Payload keys are PRIV-2's set, Active only | `ROW_KEYS` projection; `status = "Active"` | `test_the_payload_holds_exactly_the_five_keys`, `test_a_leaver_does_not_appear_for_anyone` |

**AC-45's staff-list clause** — an absent key means hidden, including when the entitlement
read failed — is met by truthiness (`features.get("plan_staff_list")`), not `is not False`.
The frame side of it is covered by
`TestTheFrameDoesNotOpenAGroupForSomebodyWhoWouldBeRefused`; the menu-entry side is not
wired (§5).

## 4. One thing I nearly got wrong, and did not

My first version added `plan_staff_list` to the OR that decides whether the **Company
group** is offered, beside `plan_policy_library` and `plan_org_structure`. That is wrong.
Those two are entries an ordinary employee may use; the staff list is an HR screen, and
`get_staff_list` refuses anyone who is not HR. On a tenant with the switch on, a plain
employee would have been given a Company group whose only new entry then refuses them.

For an HR caller `is_hr` already opens the group, so the staff list needs nothing there.
The change to `frame_api.py` is therefore a **comment recording why the line is absent**,
plus three tests that fail if somebody adds it later.

## 5. What is NOT wired, and why — read this first

**Two files are still held by slice 035 and were not touched:**
`alvoraa_portal/alvoraa_portal/www/hrms-employee.html` and
`alvoraa_portal/alvoraa_portal/hr_api.py`. `goals_api.py` and `performance_api.py` were
left alone for the same reason. Checked in `.claude/worktrees/035-wrong-numbers`, not
assumed.

So, plainly: **at the end of this stretch nobody can see a staff list on a screen.**

| Piece | State |
|---|---|
| The feature key, off everywhere until a tenant is ticked | **built** |
| `plan_staff_list` reaching the browser through `get_available_features` | **built** — the existing loop does it; no change was needed in `hr_api.py` |
| The endpoint, with its switch, scope, caps and field list | **built** |
| The **Staff list menu entry** in the Company group | **not built** — it lives in `hrms-employee.html` |
| The `#company/staff` **route and the screen itself** | **not built** — same file |
| The `plan_org_structure` gate at `hrms-employee.html:7813` being split in two | **not done** — same file. Today that one line still gates the People screen and the org chart together |
| The no-permission sentence shown for a typed `#company/staff` | **not wired.** The endpoint returns that exact sentence, so when the page is wired it has the right words to show |

What a person could actually see today: nothing new on any screen. What a person could
**do** today: call `get_staff_list` from the browser console on a ticked tenant, as an HR
user, and get a correct, scoped, capped list back — and be refused on an unticked one.

## 6. Non-functional dimensions, against the code I actually wrote

| Dimension | Verdict | One line |
|---|---|---|
| Performance | **neutral** | Two queries per call whatever the tenant's size — one page of rows, one `COUNT(*)`. Budget was 4 queries and 400 ms. Both filters hit indexed columns (`company`, `branch`, `status`). No N+1, no full child-table read. Not yet measured at 1,000 employees — `test034` is small; that measurement belongs with the screen |
| Scalability | **improves** | The list is capped at 50 server-side however large a `limit` the caller sends, and the true total is a `COUNT(*)` rather than a second full read |
| Security | **improves** | A new server-side gate where there was none: today `plan_org_structure` is checked in the browser only (`hrms-employee.html:7813`) while `search_people` itself is ungated. This endpoint checks the plan, then the scope, then Active, before it reads anything |
| Multi-tenancy | **neutral** | The scope is `permitted_employee_filters()`, the one shared rule; no new query invented. Company and branch are always in the filter dict, which can never be empty |
| Privacy | **improves** | Five fields, projected key by key on the way out, so a field added to the query cannot reach a browser without somebody editing `ROW_KEYS`. Leavers excluded. The refusal log carries the endpoint, the caller and the outcome — no name, no store, no search term, and there is a test that reads the log line and checks |
| Reliability | **neutral** | No external call, no background job, no write. Nothing to retry |
| Observability | **improves** | Every refusal is one structured line through `access.log_refusal`, greppable by endpoint and rule |
| Maintainability | **improves** | One key in the existing registry rather than a parallel switch; one endpoint file that the existing registry test now covers by one line in `MODULES` |
| Data integrity | **neutral** | Read only |
| Accessibility | **not applicable this stretch** | There is no screen yet |
| Upgrade-safety | **neutral** | Nothing outside our own apps was touched |
| Internationalisation | **neutral** | The one user-facing string goes through `_()` |

## 7. Commands I ran, and what they said

| Command | Result |
|---|---|
| `git fetch origin dev` + `git rebase origin/dev` | clean, 10 commits in, no conflicts |
| `python scripts/check_app_integrity.py` | **628 checks, OK** — and it caught a real mistake first: importing the module constant `NO_EMPLOYEES` with `from hrms... import` fails its check, because it only knows functions and classes. Changed to `import hrms.alvoraa_hr_core.access as access` |
| `bench --site test034 run-tests --module ...test_staff_list_034` | **28 OK** (9 + 19) |
| `...test_opt_in_features` | **4 FAILED first** — the `SHIPPED_OPT_IN` pin doing its job. **19 OK** after naming the key |
| `...test_frame_api_034` | 33 OK |
| `...test_frame_endpoint_registry_034` | 7 OK |
| `...test_permitted_employee_filters_034` | 10 OK (after the fixture fix in §8) |
| `...test_subscription` / `test_subscription_access` / `test_endpoint_entitlement` / `test_pricing` / `test_portal_module_gate_016` / `test_module_access` / `test_preview_page_034` | 32 / 56 / 13 / 36 / 17 / 51 / 14 OK |

### Proving the tests bite

Each guard was broken on purpose and the right tests went red.

| What I broke | What went red |
|---|---|
| The feature check (`if False and not has_feature(...)`) | `test_hr_is_refused_on_a_tenant_that_was_never_given_the_feature` |
| The `NO_EMPLOYEES` refusal, the `status = "Active"` line and the wildcard escaping, together | **9 tests** — the plain-employee and plain-manager refusals, the leaver, the wildcard, the store scope, the total, the paging and the same-sentence test |
| Added `staff_list` to the `enterprise` bundle and removed its `opt_in` | `test_it_is_in_no_plan_bundle`, `test_the_key_exists_and_is_opt_in`, `test_a_site_with_nothing_recorded_does_not_get_it` |
| Added `cell_number` to the row fields | `test_the_payload_holds_exactly_the_five_keys` |

All restored afterwards and re-run green.

## 8. Two traps found while testing — both real, both fixed

**1. The inherited fixture switched the whole feature gate off.** `_ReviewBase.setUp`,
five classes up the chain from slice 030's store fixtures, patches
`subscription.has_feature` to return `True` for everything so that the review tests are
about reviews. Inheriting those fixtures inherited the patch, and **every entitlement test
in my file passed while proving nothing** — the first run showed four failures whose real
cause was that the "off" state was unreachable. The fix stops the patch for the length of
each test and starts it again before the base stops it, and **asserts that
`has_feature` is not a `Mock`**, so this cannot go quiet again. (`test_frame_api_034` has
its own version of the same guard — the earlier stretch met this too.)

**2. My leaver fixture broke somebody else's test in the next run.** Slice 030's fixture
people are permanent on purpose, and `test_permitted_employee_filters_034` asserts the
**exact** set of people in store A. A sixth person left behind there made it fail for a
reason that had nothing to do with it. Fixed with a `tearDownClass` that deletes the
leaver, and the leftover row was removed from `test034` by hand. Verified: the module runs
twice in a row and leaves nothing behind.

## 9. Known gaps and shortcuts

- **The whole browser side of the staff list is missing** — *blocked dependency, not a
  shortcut*. §5 lists exactly what. Nothing was copied out of the held files to work
  around it.
- **No performance measurement at 1,000 employees** — *temporary debt*. The query shape is
  two bounded reads and the cap is enforced server-side, so I am confident about the
  shape, not about the number. It is removed by measuring on the PP Jewellers copy when
  the screen exists; that real-data check is already owed for this slice (SEC-5).
- **`search_people` in `alvoraa_org_structure` still escapes no wildcards** — *noticed,
  not fixed, and it is in this slice's plan*. PRIV-3 covers it under the `_search_scope`
  work, which is a different commit. My own endpoint escapes. Recorded so it is not lost.
- **The org chart is still gated in the browser only.** `plan_org_structure` is checked at
  `hrms-employee.html:7813`; `search_people` itself has no `requires_feature`. Splitting
  that line is part of this slice and waits for the file. **This is not new and this
  stretch does not make it worse**, but it should not be forgotten: it is the same class of
  hole SEC-16 exists to avoid.
- **Release gate 8 stands**: the key must be ticked on for `dtc` and `aahr`, and on the
  local PP Jewellers copy. That is a tenant configuration action and needs Surbhi's word
  on the day.

## 10. The whole-app run, and the one thing it needs before it is clean

`bench --site test034 run-tests --app alvoraa_portal` on the committed state
(`37c632e`, rebased on `origin/dev` `5640ab8`): **994 tests, 0 failures, 36 errors,
2 skipped.**

**All 36 errors are one thing, and it is not this slice.** Every one is
`Table '...tabAlvoraa Field App Daily Count' doesn't exist`. That doctype arrived with
slice 013 step 6 in the commits I rebased onto, and **`test034` has never been migrated
since**: `frappe.db.exists("DocType", "Alvoraa Field App Daily Count")` is `None` and the
table is absent. Proved by running the two modules that use it on their own —
`test_field_app_step6_013` 27 errors and `test_field_app_permissions_013` 9, which is
exactly 36. The same cause produces one extra failure in `test_field_app_step6_013`'s
migration check when that module is run alone.

**`bench migrate` would clear it, and I did not run it** — it is on the list of commands
that need Surbhi's word first. So the honest statement is: **every test that can run on
this site passes, and 36 cannot run until that site is migrated.** Nothing in this stretch
needs a migration; slice 013's does.

For the record, the modules nearest this change were also run on their own and are green:
`test_staff_list_034` **31**, `test_opt_in_features` 19, `test_frame_api_034` 33,
`test_frame_endpoint_registry_034` 7, `test_preview_page_034` 14,
`test_permitted_employee_filters_034` 10, `test_subscription` 32,
`test_subscription_access` 56, `test_endpoint_entitlement` 13, `test_pricing` 36,
`test_portal_module_gate_016` 17, `test_module_access` 51, `test_review_fixround_010d` 44.

**One earlier full run is not quoted as a result**, deliberately: I edited files while it
was running and started a second run against the same database, which deadlocked. It is
worth naming because it is what found the weakness in my own `has_feature` guard — in a
whole-app run other modules patch the same function, patchers stack, and stopping the
innermost one restores the *next* mock rather than the real function. The guard now
patches the real function back explicitly and asserts it is not a `Mock`. One of my own
tests was also fragile and is fixed: it read the first page of the whole company and
assumed the fixture people were on it, which stops being true above 50 Active employees —
the cap doing its job.
