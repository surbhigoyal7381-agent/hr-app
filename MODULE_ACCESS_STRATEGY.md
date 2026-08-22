# Module access by subscription plan — strategy

**Status:** proposal, awaiting approval. Nothing here is built yet.
**Scope:** the whole tenant — Frappe desk, Frappe HR, and our portal. Not just the wrapper.

---

## 1. What is true today

Verified on `dev.alvoraa.co`, 2026-08-22.

### The subscription boundary does not exist

`site_config.json` records `modules_enabled` for every tenant. Across the entire codebase
it is read in three places: two that write it, one that displays it in the admin console.
**Nothing reads it to allow or deny anything.**

### Provisioning contradicts itself

`deploy/provision_tenant.sh` installs every app unconditionally, whatever was ticked:

```bash
bench --site "$SITE_NAME" install-app erpnext
bench --site "$SITE_NAME" install-app hrms
bench --site "$SITE_NAME" install-app alvoraa_portal
bench --site "$SITE_NAME" install-app alvoraa_goals
```

while `tenant_api._run_install_modules` carries logic to install two of those *only when
the plan needs them* — logic that can never fire, because they are already installed.

### The base application is wide open, and that is the bigger problem

| Measured on the demo tenant | |
|---|---|
| Enabled users | 125 |
| **System Users** (can open `/app`) | **88** |
| …of those, **ordinary employees** with no HR role | **85** |
| Module Defs visible in the desk | **39** (21 erpnext, 11 frappe, 3 hrms, 4 ours) |

So 85 shop-floor employees can open the Frappe desk and browse **Accounts, Buying, CRM,
Manufacturing, Assets, Projects, Stock** and the rest. No subscription plan is involved —
this is true on every plan, today.

Hiding a Goals menu in our portal while this is the case would be painting a door on a
wall that has no wall.

---

## 2. The four surfaces a tenant can reach

Any control has to cover all four, or it is not a boundary.

| Surface | What it exposes | Gated today? |
|---|---|---|
| **Our portal** `/hrms-employee` | leave, attendance, expenses, goals | ❌ |
| **Frappe desk** `/app` | all 39 modules, every doctype the role allows | ❌ |
| **Frappe HR PWA** `/hrms` | leave, claims, attendance | ❌ |
| **REST API** `/api/method/...` | everything, to anyone logged in | ❌ |

The first three are user interfaces. **The fourth is the only one that decides anything** —
the others are windows onto it.

---

## 3. The mechanisms Frappe gives us

All verified present on the running site.

| Mechanism | What it really does | Enforces? |
|---|---|---|
| `user_type` = *Website User* | removes desk access completely | ✅ yes |
| **Module Profile** → `User.block_modules` | hides modules from the desk UI | ❌ **UI only** |
| **Roles + Role Permissions** | grants or denies doctype access, server-side | ✅ yes |
| **App not installed** | the doctypes do not exist | ✅ strongest |
| **Domain Settings** | hides irrelevant ERPNext modules | ❌ UI only |

**The important distinction:** blocking a module hides it from the sidebar. It does **not**
stop `/api/resource/Salary Slip` if the user's role permits it. Only roles, permissions and
app installation actually deny anything.

Two structural facts that constrain the design:

- **Payroll is its own module** (`Module Def: Payroll`), so it can be blocked and role-gated.
- **Recruitment is not.** `Job Opening`, `Job Applicant` and `Interview` all live in the
  `HR` module. It cannot be module-blocked without taking Core HR with it — it has to be
  handled by roles.

---

## 4. Proposed model — five layers

Ordered by how much they actually protect, not by how visible they are.

### Layer 0 — Most employees should not be System Users

85 ordinary employees hold desk access they never use; the portal is their interface.
Making them **Website Users** removes the entire desk surface in one move — 39 modules gone
for 85 people, before any plan logic exists.

This is the single highest-value change in this document, and it is not plan-specific.

> Care needed: `user_type` affects what Frappe HR's own PWA allows, and Website Users
> cannot hold most desk roles. Wave 1 proves it on one user before any bulk change.

### Layer 1 — Install only what the plan includes

Fix `provision_tenant.sh` so `alvoraa_goals` and `alvoraa_portal` are installed only when
`goals` / `vendor` are in the plan. If the app is absent, its doctypes do not exist and no
API can reach them. This is the strongest gate available and it costs nothing to apply at
provisioning time.

`erpnext` cannot be dropped — Frappe HR depends on it.

### Layer 2 — A Module Profile per plan

Create a Module Profile on the tenant site listing the modules that plan does **not** get,
and set it as the default for new users. Blocks:

- **always**: the 21 `erpnext` modules an HR tenant has no use for (Accounts, Buying,
  Manufacturing, …)
- **by plan**: `Payroll` when payroll is off; `Alvoraa Goals` when goals is off

This is what makes the desk *look* like an HR product instead of a full ERP. It is
cosmetic — layer 3 is what makes it true.

### Layer 3 — Roles carry the enforcement

Withhold the roles that grant access to disabled features, and remove them on downgrade:

| Module off | Roles withheld |
|---|---|
| payroll | payroll/salary roles on that site |
| recruitment | `Interviewer`, and recruitment doctype permissions (no module of its own) |
| goals | roles created by `alvoraa_goals` |
| vendor | vendor/supplier portal roles |

This is the layer that survives a direct API call.

### Layer 4 — Our portal

`requires_module` decorator on whitelisted endpoints, route guards on portal pages, then
hide the nav items using the mechanism `get_available_features()` already provides.

---

## 5. One source of truth

The plan→modules map is currently duplicated three times (`tenant_api._preset_map` twice,
and `MODULE_PRESETS` in the admin JavaScript). One registry in Python, exported to the
front end and consumed by provisioning:

```python
MODULES = {
    "hrms":        {"label": "Core HR", "required": True},
    "payroll":     {"label": "Payroll",     "module_defs": ["Payroll"]},
    "recruitment": {"label": "Recruitment", "roles": ["Interviewer"]},   # no module of its own
    "vendor":      {"label": "Vendor Portal", "app": "alvoraa_portal"},
    "goals":       {"label": "Goals",         "app": "alvoraa_goals"},
    "analytics":   {"label": "Analytics"},
}
```

Each module declares how it is gated — app, module def, roles — so provisioning, the
portal and the admin console all read the same definition.

---

## 6. Delivery

| Wave | What | Risk |
|---|---|---|
| **1** | Module registry + `requires_module` + tests. Prove Website User conversion on ONE user | none — nothing enforced yet |
| **2** | Layer 0: convert ordinary employees to Website Users on dev, verify the portal still works | medium — reversible per user |
| **3** | Layer 2: Module Profile per plan, blocking erpnext modules + plan modules | low — UI only |
| **4** | Layer 3: role withholding, applied at provisioning | **highest** — this denies access |
| **5** | Layer 1: provisioning installs only what the plan includes | low for new tenants |
| **6** | Layer 4: portal API/route/UI gating | low |

Wave 2 alone removes most of the exposure. Wave 4 is where a mistake locks someone out, so
it lands after the rest is proven and with a tested rollback.

---

## 7. Decisions needed

1. **Downgrade behaviour** — hide and keep the data (recommended), or uninstall the app?
   `bench uninstall-app` drops tables; I would never do that automatically.
2. **Existing tenants** — apply layer 0 to the 85 employees on dev/demo now, or only to
   newly provisioned tenants? I recommend dev first, verify, then demo.
3. **`recruitment` has no portal screen** and no module of its own. Should it be sold at
   all yet?
4. **Does the plan gate apply to the tenant's own Administrator?** I would say yes, or the
   boundary depends on who is logged in.
5. **ERPNext modules** — block all 21 for every HR tenant, or keep a few (Projects? CRM?)
   for future plans?

---

## 8. Risks

| Risk | Handling |
|---|---|
| Converting users to Website User breaks their portal login | Prove on one user in wave 2 before any bulk change; reversible per user |
| Removing a role locks out a real user | Wave 4 last, after the rest is proven, with the previous roles recorded so they can be restored |
| Module Profile mistaken for security | Layer 3 lands before anyone is told the boundary exists |
| Existing tenants lose access on deploy | All three live sites are `enterprise`; verify before shipping |
| Missing `modules_enabled` on older sites | Absent means "everything on" — no tenant is locked out by an upgrade |

---

## 9. What I need from you

Approval of the shape and answers to §7. I would then build **wave 1** and show you the
registry, the decorator and the single-user Website User experiment before anything is
applied at scale.
