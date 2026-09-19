# Slice 024 — the employee portal is the landing page, in code

Approved by the user on 2026-09-19 ("let's make this B change"): the code decides,
not a per-site field. Local only. Nothing is pushed.

## 1. What the user asked for

Typing `https://<tenant>/` and logging in should both land on `/hrms-employee`,
without anyone configuring the site.

## 2. What the code does today

### The bare address `/`

Nothing sends it anywhere. `frappe/website/path_resolver.py:205` turns the empty
path into `get_home_page()`, and `get_home_page()` (frappe v16, `website/utils.py:98`)
tries, first match wins:

| # | Source | On ppj.localhost |
|---|---|---|
| 1 | `home_page` on any of the user's Role records | none set (checked: zero rows) |
| 2 | `Portal Settings.default_portal_home` | not set |
| 3 | hooks — `get_website_user_home_page` (a function) → `website_user_home_page` → `role_home_page` → `home_page` | **none of our apps set any of these** |
| 4 | `Website Settings.home_page` | not set |
| 5 | fallback | `login` for Guest, `me` otherwise — and `me` becomes `desk` for a System User |

So today `/` lands a signed-in employee on `/app`. That is the whole bug.

### Logging in

Already handled, and correctly: `alvoraa_portal/auth.py:on_login` is wired as the
`on_login` hook and sets `frappe.local.response["home_page"]`. The branded login page
also calls `auth.get_portal_redirect()`. Both use the same rule.

**So the gap is only the bare address**, plus any path that goes through
`get_home_page()` (OAuth landing, `frappe/www/login.py` for a Website User).

### The rule that already exists, and is already approved

`alvoraa_portal/auth.py` says it plainly in its docstring:

> Anyone with an Employee record lands in the portal, HR and managers included …
> A tenant's HR admin usually also holds System Manager, so seniority alone must
> not route someone to `/app` — only the absence of an Employee record does.

`Administrator` is excluded by name. A platform operator account (System Manager or
Administrator, no Employee record) keeps the desk.

## 3. Two real defects found while reading

**D1 — `_portal_home_for` can land a user on a page their plan does not include.**
It returns `/vendor-portal` for a Vendor User and `/driver-portal` for a Delivery
Partner, with no plan check. Slice 016 made both pages raise `DoesNotExistError`
when the tenant does not have the `vendor` feature. So on a Starter tenant that
happens to hold a Vendor User row, login already lands on a 404. Wiring the same
helper to `/` would spread that 404 to the front door. **Fixed in this slice.**

**D2 — the branded login page contradicts `on_login`.** `www/alvoraa_login.py`
sends an already-signed-in HR Manager / HR User / Accounts user to `/app`, while
`auth.on_login` sends the same person to the portal. Two rules, two answers.
**Not fixed here** — it changes behaviour the user has not ruled on. Raised for her.

### The portal feature itself

There is no such thing as a tenant without `/hrms-employee`.
`subscription.FEATURES["portal"]["required"] = True`, and `has_feature()` returns
True for any required feature whatever the site's `features` list says. `/hrms-employee`
is therefore safe as the universal fallback. The plan risk is entirely D1.

## 4. Chosen strategy

**Hook: `get_website_user_home_page`**, pointed at one function.

| Candidate | Why not |
|---|---|
| `home_page = "hrms-employee"` | One answer for everybody. Sends Administrator, System Manager and vendor users to the employee portal. Wrong for three of the five cases. |
| `role_home_page` | Keyed on role only. Cannot ask "does this person have an Employee record", cannot check the plan, and the role loop picks whichever role it meets first. |
| `get_website_user_home_page` | Takes the user, returns a path or `None`. `None` means "Frappe, carry on" — which is exactly what an operator and a Guest need. It can reuse the rule that already governs login. **Chosen.** |

One rule, two entry points. `auth.home_page_for(user)` becomes the single source of
truth; `on_login` and `get_portal_redirect` call it too, so `/` and login can never
drift apart.

### What each kind of user gets

| User | Result | Why |
|---|---|---|
| Employee, no desk role | `/hrms-employee` | has an Employee record |
| HR Manager / HR User who is an employee | `/hrms-employee` | seniority does not route; the portal covers their work |
| System Manager / Administrator with **no** Employee record | `None` → Frappe default → `/desk` → `/app` | platform operators need the back office |
| `Administrator` | `None` → `/app` | excluded by name, as in `on_login` |
| Vendor User / Delivery Partner, tenant **has** `vendor` | `/vendor-portal` / `/driver-portal` | unchanged |
| Vendor User / Delivery Partner, tenant **lacks** `vendor` | `/hrms-employee` | D1 fix — never land on a 404 |
| Guest | `None` → Frappe's `login` → our `/alvoraa-login` redirect | the login page must keep working |

`/app` still works for everyone with desk access: `get_home_page()` decides only where
`/` and a post-login landing point. It is not a redirect away from `/app`.

## 5. Impact

**Cross-module.** `alvoraa_portal` only. `hrms`, `alvoraa_goals` and `hrms/hooks.py`
are untouched (the `home_page` lines there are commented-out Frappe boilerplate).
Callers of `_portal_home_for`: `auth.on_login`, `auth.get_portal_redirect`,
`www/alvoraa_login.py`. All three keep the same signature and the same answer, except
for the D1 fix.

**Personas.** CXO and HR Manager: `/` now lands on the portal instead of the desk;
`/app` is one click away and unchanged. Employee: `/` works instead of dropping them
into a desk they cannot use. Platform operator: nothing changes.

**HRMS domain.** No doctype, no field, no leave/attendance/payroll logic touched.

## 6. Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **improves** | Two `frappe.db.exists` calls disappear on every login for tenants without the `vendor` feature. `get_home_page()` caches per user (`frappe.cache.hget("home_page", user, …)`), so `/` costs at most two indexed existence checks once per user. |
| Security | **neutral** | No permission is granted or widened. The function only picks a URL; every page behind it keeps its own guard (`hrms_employee.py` bounces Guest, the vendor pages 404 off-plan). |
| Reliability | **improves** | D1 goes away, and the function is wrapped so a lookup failure returns `None` (Frappe's own behaviour) rather than breaking the front door. |
| Scalability | **neutral** | Per-user cached, O(1), no growth with headcount. |
| Maintainability | **improves** | One rule instead of two; `/` and login can no longer disagree. |
| Data integrity | **neutral** | Reads only. The `home_page` cache is a user cache key, cleared by `frappe.clear_cache(user)` when the User doc is saved — which is what happens when an Employee record is linked. Login never reads the cache, because `on_login` sets the value directly. |
| Compliance / privacy | **neutral** | No personal data is read beyond "does a row exist", none is logged, and nothing new is shown to anyone. |
| Accessibility | **neutral** | No UI change. |
| Upgrade-safety | **improves** | A hook in our own app. No upstream file touched. |
| i18n | **neutral** | No user-facing string. |

## 7. Parallel-work check

`git fetch origin`: **nothing came in.** Local `dev` is two commits ahead of
`origin/dev` (`4f35960`, `d1fd9c6` — deploy runbook and registry token, not mine).

| File I will change | Hot file? | Who else is in it |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/auth.py` | no | no board row claims it |
| `alvoraa_portal/alvoraa_portal/hooks.py` | **yes** | board rows for 010 and 014 claim `doc_events` in this file. I add one line in its own section at the top, nowhere near `doc_events`. |
| `alvoraa_portal/alvoraa_portal/tests/test_home_page_024.py` | new file | nobody |

Slices 013–016 and 018 belong to other sessions. None of their files are touched.
The main checkout holds other sessions' uncommitted edits in `ux-learnings.md`,
`alvoraa_position.py`, `KPI_AUTOMATION_BACKLOG.md` and several untracked docs — none of
mine, none staged, none touched.

**Pin test:** `test_home_page_024.py` names the hook and every routing answer, so a bad
merge that drops the hook line or loosens the rule fails CI.

## 8. Open questions for the user

1. **D2** — should the branded login page stop sending a signed-in HR Manager to `/app`,
   so it agrees with everything else? Behaviour change; her call.
2. A tenant that sets its own `Website Settings.home_page` will be **ignored** for
   employees, because hooks are checked before Website Settings. That is the point of
   the code-wide choice, but it is worth knowing.
