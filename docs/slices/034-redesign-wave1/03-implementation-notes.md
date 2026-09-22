---
slice: 034-redesign-wave1
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-23
status: stretch 1 of the build complete — local only, not pushed, not merged
covers: the new-file work only. US-10 (the page split) and SEC-13 (the Team query) are NOT started
base: slice/034-redesign-wave1, rebased onto origin/dev (da2193d)
commits: 3e3b895, 328d5a0, 1fb9727
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
| AC-40, AC-74, AC-65 (SEC-1) | **met at `get_context`; owed over HTTP** | See §6 |
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

**Also checked over HTTP: no.** The 404/403/redirect decisions are asserted at
`get_context`, which is where both are made, and the status codes are asserted from
Frappe's own exception classes. A real `curl` pass on the bench with `portal_preview` set
and unset is **owed** before this slice is called done.

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
- **AC-40/AC-74 not exercised over real HTTP** — *temporary debt*. Removed by one curl pass
  on the bench with the flag set and unset.
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
