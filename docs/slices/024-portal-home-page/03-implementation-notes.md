# Slice 024 — implementation notes

Local only. Not merged into local `dev`, not pushed.
Branch `slice/024-portal-home-page`, worktree `.claude/worktrees/024-portal-home-page`,
cut from local `dev` at `4f35960`.

## What was built

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/hooks.py` | **configure** — one hook line | `get_website_user_home_page = "alvoraa_portal.auth.home_page_for"`. Added in its own commented section at the top, well away from the `doc_events` block that slices 010 and 014 claim. |
| `alvoraa_portal/alvoraa_portal/auth.py` | **extend** — new function `home_page_for(user)` | The single rule for where a user belongs. `on_login` and `get_portal_redirect` now call it, so the three doors cannot drift apart. `_portal_home_for` keeps its signature and gains the vendor plan check. |
| `alvoraa_portal/alvoraa_portal/tests/test_home_page_024.py` | new | 15 pin tests. |

No new DocType, no custom field, no patch, no upstream file touched.

## Why `get_website_user_home_page`

Frappe v16.33.1, `frappe/website/utils.py:get_home_page_via_hooks()`, tries
`get_website_user_home_page` (a function) → `website_user_home_page` (a string) →
`role_home_page` (role → page) → `home_page` (a string).

- `home_page` gives one answer to everybody, so Administrator, a platform operator
  and a vendor user would all be sent to the employee portal. Wrong for three of the
  five cases the user asked about.
- `role_home_page` is keyed on role. It cannot ask "does this person have an Employee
  record", cannot check the plan, and picks whichever of the user's roles it meets
  first. Our HR people hold several roles.
- `get_website_user_home_page` receives the user and may return `None`, meaning
  "Frappe, carry on". `None` is exactly what a platform operator needs (Frappe sends a
  System User to the desk) and what Guest needs (Frappe sends them to `login`). It is
  the only one of the four that can express the rule honestly.

No other installed app sets any of these four hooks (checked `frappe`, `erpnext`,
`hrms`), so ours is unambiguous — which matters, because Frappe takes `[-1]`.

## Who lands where

| User | Landing page | How |
|---|---|---|
| Employee, no desk role | `/hrms-employee` | has an Employee record |
| HR Manager / HR User who is an employee | `/hrms-employee` | seniority does not route; this is the rule `auth.py` already applied at login |
| System Manager / Administrator with **no** Employee record | `None` → Frappe default → the desk | platform operators work in the back office |
| `Administrator` | `None` → the desk | excluded by name |
| Vendor / driver user, tenant has `vendor` | `/vendor-portal` / `/driver-portal` | unchanged |
| Vendor / driver user, tenant lacks `vendor` | `/hrms-employee` | new — see D1 below |
| Guest | `None` → `login` → our `/alvoraa-login` redirect | the sign-in page is untouched |

`/app` still works for everyone with desk access. `get_home_page()` decides only where
`/` and a post-login landing point; it is not a redirect away from the desk.

## The plan question

There is no tenant without the employee portal. `subscription.FEATURES["portal"]`
carries `required: True`, and `has_feature()` returns True for a required feature
whatever the site's `features` list says. `/hrms-employee` is therefore always a safe
fallback.

**D1, a real defect found and fixed.** `_portal_home_for` returned `/vendor-portal`
and `/driver-portal` with no plan check. Slice 016 made both pages raise
`DoesNotExistError` when the tenant lacks the `vendor` feature. So a Starter tenant
that still held an old Vendor User row was landing that person on a 404 at every
login. Wiring the same helper to `/` would have spread that to the front door. The
vendor lookups now happen only when `has_feature("vendor")` is true, which also saves
two existence queries per login on every tenant without the feature.

## D2, found and **not** fixed

`www/alvoraa_login.py` sends an already-signed-in HR Manager, HR User or Accounts user
to `/app`, while `auth.on_login` sends the same person to the portal. Two rules, two
answers, in the same app. It only shows when somebody types the login URL while already
signed in. Fixing it changes behaviour the user has not ruled on, so it is raised, not
changed.

## Acceptance

| What was asked | How it is met |
|---|---|
| `https://<tenant>/` lands on `/hrms-employee` | the hook answers `get_home_page()`, which is what `path_resolver.resolve_path` uses for the empty path |
| logging in lands on `/hrms-employee` | already worked via `on_login`; now driven by the same function |
| no per-site configuration | a hook in our app, shipped in the image; no Website Settings, no Role, no Portal Settings row |
| an admin keeps the desk | an account with a desk role and no Employee record gets `None` |
| never land on a page the plan excludes | D1 fix; `portal` is a required feature so the fallback is always valid |
| Guest still reaches the login page | `home_page_for` returns `None` for Guest, so Frappe's `login` stands |

## Non-functional, against the code as written

| Dimension | Before → after | Note |
|---|---|---|
| Performance | **improves** | Two `frappe.db.exists` calls removed per login on tenants without `vendor`. `/` costs at most two indexed existence checks, cached per user by `frappe.cache.hget("home_page", user, …)`. |
| Security | **neutral** | Picks a URL only. No permission granted, nothing made visible. Every page keeps its own guard. |
| Reliability | **improves** | D1 gone; the function is wrapped so a lookup failure returns `None` rather than breaking the front door of a live tenant. |
| Scalability | **neutral** | O(1), per-user cached, no growth with headcount. |
| Maintainability | **improves** | One rule in one function, used by three doors. |
| Data integrity | **neutral** | Reads only. |
| Compliance / privacy | **neutral** | Reads "does a row exist" and nothing else. The error log line carries no user, no email, no document. Nothing new is shown to anybody. |
| Accessibility | **neutral** | No UI change. |
| Upgrade-safety | **improves** | A hook in our own app; no upstream file touched. |
| i18n | **neutral** | No user-facing string. |

## NFR detail

- **Queries:** 1 (`Employee` by `user_id`) for a staff member; up to 3 for a vendor user
  on a vendor-enabled tenant; 0 extra for Guest and Administrator (both return early).
- **Indexes:** none added. `Employee.user_id`, `Vendor User.email` and
  `Delivery Partner.primary_email` are existing single-value lookups.
- **Background jobs:** none.
- **Permission enforcement:** unchanged, and deliberately so. The landing page is not a
  permission. `/hrms-employee` bounces Guest; the vendor pages 404 off-plan.
- **Sensitive fields:** none read or written.
- **Fallback:** any exception returns `None`, which is precisely Frappe's own
  behaviour without the hook.
- **Cache staleness:** `home_page` is a Frappe *user* cache key, cleared by
  `frappe.clear_cache(user)` — which happens when the User doc is saved, and linking an
  Employee record saves the user. Login is never stale, because `on_login` sets the
  value directly rather than reading the cache. Only the bare `/` could serve a stale
  answer, and only until the user's cache is next cleared.

## What a tenant that set its own Website Settings home page will do

It will be **ignored for staff**. `get_home_page()` checks hooks *before*
`Website Settings.home_page`, so our function wins for anybody with an Employee record.
For a platform operator our function returns `None`, and their Website Settings value
then applies as before. Two things still outrank the hook, and neither is set on any
tenant today: `home_page` on a Role record, and `default_workspace` on the User.

## Tests run, and what they said

All on the shared `test_site`, in a throwaway container `hrlocal-024` that mounted this
worktree as `apps/alvoraa_portal` (the pattern slices 013 and 022 used). **Local `dev`
was not touched** — the user sequences merges. The container has been removed.

Slice 013 was running a full `alvoraa_portal` suite on `test_site` when this work
started; it released the site at 06:53 and only then did anything here run. One run at
a time throughout.

| Run | Result |
|---|---|
| `alvoraa_portal.tests.test_home_page_024` | **15 tests, OK** |
| `alvoraa_portal.tests.test_portal_security_010` | 45 + 5 tests, OK |
| `alvoraa_portal.tests.test_module_access` | 51 tests, OK |
| `alvoraa_portal.tests.test_access_control` | 34 tests, OK |
| full `bench run-tests --app alvoraa_portal` | 584 + 673 = **1,257 tests, OK** (4 skipped), no failures, no errors |
| `python scripts/check_app_integrity.py` | 593 checks, "OK - all consistent" |
| `Custom DocPerm` before / between / after | **228 rows, 45 doctypes — unchanged at every checkpoint** |

### The fail-without-fix proof

A throwaway script piped in on stdin, run in-process against `test_site`, switching the
fix off twice and putting it back, then rolling the whole thing back. Nothing was copied
into any container.

```
=== WITH THE FIX ===
  PASS  employee lands on the portal                                got='hrms-employee'
  PASS  vendor user off-plan does NOT go to the 404 vendor page     got='hrms-employee'
  PASS  vendor user on-plan still goes to the vendor portal         got='vendor-portal'
=== WITHOUT THE HOOK (the bug as it was) ===
  PASS  hook removed -> no landing page from hooks                  got=[]
  PASS  hook removed -> the employee is dropped in the desk         got='me'
=== WITHOUT THE PLAN CHECK (defect D1 as it was) ===
  PASS  plan check removed -> landed on the page slice 016 made 404 got='vendor-portal'
=== BACK WITH THE FIX ===
  PASS  vendor user off-plan is safe again                          got='hrms-employee'

7 of 7 checks as expected. Rolled back.
```

`'me'` is Frappe's own fallback for a signed-in user with no landing page. In a real
request it becomes `desk` — `_get_home_page` turns `me` into `desk` when
`frappe.session.data.user_type == "System User"`, and all our staff accounts are System
Users. The script sets the user with `frappe.set_user`, which clears `session.data`, so
the conversion does not fire there. Either way it is not the portal, which is the point.

## Two Frappe facts worth writing down

1. `get_home_page_via_hooks()` returns the **empty list**, not `None`, when nothing in
   the chain answers — it assigns `frappe.get_hooks("home_page")` and hands back `[]`.
   It is falsy and every caller tests `if not home_page`, but a test asserting `is None`
   fails for the wrong reason. The test file has a helper and a comment about it.
2. `test_site` carries only one Gender row, `Male`. The fixture asks the site what it
   has rather than naming one.

## Known gaps

- `from frappe import _` in `auth.py` is unused and ruff flags it. It was unused before
  this slice; removing it is unrelated noise in a file other sessions may touch, so it
  is left alone.
- D2 above.
- The hook does not cover `frappe/www/login.py`'s already-signed-in branch for a System
  User, which hard-codes `/desk`. Our `website_redirects` sends `/login` to
  `/alvoraa-login` first, so it is not reachable in normal use.
