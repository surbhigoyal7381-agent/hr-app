# Module access by subscription plan — strategy

**Status:** proposal, awaiting approval. Nothing here is built yet.

---

## 1. What is true today

Verified on the running system, 2026-08-22.

**The plan is recorded but never enforced.** `site_config.json` holds
`modules_enabled` for every tenant. Searching the whole codebase, that value is read in
exactly three places:

| Where | What it does |
|---|---|
| `tenant_api.list_tenants` | shows the module list in the admin console |
| `tenant_api.update_tenant` | writes the value |
| `auth.get_branding` | returns it to the login page, unused |

**Nothing reads it to allow or deny anything.** That is the whole bug.

**Every tenant gets every app.** `deploy/provision_tenant.sh` installs `erpnext`,
`hrms`, `alvoraa_portal` and `alvoraa_goals` unconditionally, whatever the operator
ticked:

```bash
bench --site "$SITE_NAME" install-app alvoraa_portal
bench --site "$SITE_NAME" install-app alvoraa_goals
```

Meanwhile `tenant_api._run_install_modules` contains careful logic to install those two
apps *only when the plan needs them*. That code can never do anything useful, because
provisioning already installed them. Two parts of the system disagree about how modules
are meant to work.

**A pattern for hiding already exists**, and it works. `get_available_features()` returns
flags, and the portal hides navigation with them:

```js
if (navEl) navEl.style.display = map[k] ? "flex" : "none";
```

That is the right shape for the UI half of this. It is only half.

---

## 2. The principle that decides the design

> **Hiding a menu is not access control.**

A hidden nav item is still a reachable URL, and every portal screen is backed by a
whitelisted API that anyone logged in can call directly with `curl`. We proved this exact
class of gap yesterday: the tenant admin console was hidden from tenants by a role check,
and a System Manager on a tenant site could still open it.

So the ask — "hide the modules" — is the visible part of the job, and I will do it. But
shipping only that would give the appearance of a subscription boundary while a customer
on the Starter plan can still read payroll data by calling the API. That is worse than
having no boundary, because everyone believes there is one.

**Three layers, in this order of importance:**

| Layer | Stops | Without it |
|---|---|---|
| **1. API gate** | a direct call to a paid endpoint | the boundary is decorative |
| **2. Route gate** | typing `/vendor-portal` in the address bar | a bookmark bypasses it |
| **3. UI hiding** | seeing menus you cannot use | confusing, but harmless |

Layer 3 is what was asked for. Layers 1 and 2 are what make it real.

---

## 3. One source of truth

Today the plan→modules mapping is duplicated in `tenant_api` (`_preset_map`, twice) and in
the admin page JavaScript (`MODULE_PRESETS`). Three copies will drift.

Proposal: one module registry in Python, exported to the front end through the existing
context call.

```python
MODULES = {
    "hrms":        {"label": "Core HR",     "required": True},
    "payroll":     {"label": "Payroll"},
    "recruitment": {"label": "Recruitment"},
    "vendor":      {"label": "Vendor Portal"},
    "goals":       {"label": "Goals"},
    "analytics":   {"label": "Analytics"},
}

PLANS = {
    "starter":    ["hrms"],
    "business":   ["hrms", "payroll", "vendor"],
    "enterprise": list(MODULES),
}
```

`hrms` is `required: True` and can never be switched off — the portal has no meaning
without leave and attendance.

---

## 4. What each module controls

Mapped against the panels and pages that actually exist.

| Module | Portal panels | Separate pages | APIs to gate |
|---|---|---|---|
| `hrms` *(always on)* | home, attendance, finances (expenses), shift/attendance/advance requests | — | — |
| `payroll` | Finances → **Salary Slips** tab | — | salary slip endpoints |
| `recruitment` | *(none yet — desk only)* | — | — |
| `vendor` | — | `/vendor-portal`, `/driver-portal` | `vendor_portal_api`, delivery endpoints |
| `goals` | **goals** panel | `/goals-portal` | `goals_api`, `alvoraa_goals` endpoints |
| `analytics` | **analytics** panel, org-settings reports | — | `get_hr_analytics` and related |

Two things fall out of this:

- **`recruitment` has no portal surface at all.** Selling it as a module today buys the
  customer nothing they can see. Either it should not be offered yet, or it needs a
  screen. Worth deciding before it appears on a price list.
- **`team` and `org-settings` are role-driven, not plan-driven.** A manager sees Team
  because they have reports. Leave them out of this mechanism.

---

## 5. How the gate works

### Layer 1 — API

A decorator, applied to whitelisted endpoints:

```python
@frappe.whitelist()
@requires_module("goals")
def get_goal_tree(...):
    ...
```

`requires_module` reads `modules_enabled` from `frappe.conf` — the site's own config, so a
tenant cannot alter it — and raises `PermissionError` when the module is off. Reading
`frappe.conf` is free; there is no query and nothing to cache.

### Layer 2 — Routes

Portal pages get the same check in `get_context`, raising `DoesNotExistError` so the page
does not exist rather than refusing politely — the same fix applied to the admin console
yesterday.

### Layer 3 — UI

Extend the existing `get_available_features()` response with the module flags, and hide
nav items and tabs with the mechanism already in place. No new front-end machinery.

---

## 6. Delivery

Small waves, each shippable and testable on its own.

| Wave | What | Why first |
|---|---|---|
| **1** | Module registry, single source of truth, `requires_module` decorator, tests | Everything else depends on it |
| **2** | Gate the `goals` and `vendor` APIs and routes | Whole modules with clear edges — the easiest to prove |
| **3** | UI hiding for goals, vendor, analytics, payroll tab | The visible change |
| **4** | Make provisioning honour the plan — install only what is needed | Fixes the contradiction in §1 |
| **5** | Plan changes: what happens on upgrade and downgrade | Needs the rest working first |

---

## 7. Decisions needed before building

**1. What happens to data when a plan is downgraded?**
If a customer drops Goals, their goals still exist. Options: hide but keep (reversible,
recommended), or uninstall the app (destructive, and `bench uninstall-app` drops tables).
I would hide and keep, and never uninstall automatically.

**2. Should the Frappe desk be gated too?**
This strategy covers the portal. A tenant admin with desk access at `/app` can still see
every module's workspaces and doctypes. Gating that means Module Def and role work, and
is a larger job. My view: portal first, desk noted as a known gap rather than pretended
about.

**3. Should `recruitment` be sold before it has a screen?** See §4.

**4. Does the plan gate apply to the Administrator?**
I would say yes for tenant sites — otherwise the boundary depends on who is logged in.
The control plane is separate and unaffected.

---

## 8. Risks

| Risk | Handling |
|---|---|
| A gate blocks something Core HR needs | `hrms` is required and ungated; wave 2 covers only self-contained modules |
| Existing tenants lose access on deploy | All three live sites are `enterprise`, so nothing changes for them. Verify before shipping |
| The flag is missing on older sites | Absent `modules_enabled` means "everything on", so no tenant is locked out by an upgrade |
| Hiding is mistaken for security | Layer 1 lands **before** layer 3, so the boundary is real before it looks real |

---

## 9. What I need from you

Approval of the shape, plus answers to §7. Then I would build wave 1 and show you the
decorator and its tests before going further — it is the piece everything else rests on.
