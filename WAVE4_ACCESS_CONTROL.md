# Wave 4 — real access control, not hiding

**Status:** proposal. Nothing built.
**Written:** 2026-08-24, after three separate attempts to fix this by hiding.

---

## 1. Why hiding kept failing

Three levers were built, in this order, each after the previous one turned out to
be insufficient:

| Lever | Hides | Found insufficient because |
|---|---|---|
| `block_modules` | the module list | Frappe HR keeps Leaves, Payroll, Recruitment and Tenure inside two shared modules |
| `Workspace.is_hidden` | workspaces | the desk sidebar is not built from workspaces |
| empty `Workspace Sidebar` | auto-generated module sidebars | the apps also *ship* sidebars as records |

Measured on a real tenant after all three: it still showed `payroll`,
`recruitment`, `tenure`, `crm` and `projects`.

The reason is in `frappe/desk/desk_views.py`:

```python
if item_type == "doctype":
    return name in self.can_read and name in self.restricted_doctypes and frappe.has_permission(name)
if item_type == "report":
    return ... and name in self.allowed_reports
```

Every item type except `workspace` is decided by **permissions**. So no amount of
hiding removes them, and each new menu Frappe adds is a new hole. This is the
last time we should be plugging one.

**And hiding was never the requirement.** A hidden Payroll still answers
`/api/resource/Salary Slip`. The ask was that unsold modules "need not be
accessible to anyone on this tenant".

---

## 2. Why withholding roles does not work either

That was the original wave 4 plan. It is wrong, and the tenant's own permission
table says so:

```
HR Manager  has read on:  HR, Payroll, CRM, Projects, Alvoraa Goals
Employee    has read on:  HR, Payroll, CRM, Projects, Quality Management
All         has read on:  parts of Accounts, HR, Buying
```

The unwanted access rides on roles the tenant **must** keep. You cannot take
`HR Manager` away from an HR manager. `All` is held by every user alive.

Withholding roles still has a place — `Interviewer` should not be granted on a
plan without Recruitment — but it is a footnote, not the mechanism.

---

## 3. The mechanism: Custom DocPerm

Frappe supports per-site permission overrides. From `frappe/permissions.py`:

```python
doctypes_with_custom_perms = get_doctypes_with_custom_docperms()
for p in perms:
    if p.parent not in doctypes_with_custom_perms:
        custom_perms.append(p)
```

**Once any Custom DocPerm row exists for a doctype, its standard permissions are
ignored completely.** That is the whole lever, and the whole danger.

So for each doctype in a blocked module we write Custom DocPerm rows containing
only the roles that stay exempt. Every other role loses access — from the API,
the list view, the sidebar and the search bar at once.

Reversal is a delete: remove the Custom DocPerm rows and the standard ones apply
again. Frappe ships `reset_perms(doctype)` to do exactly that.

---

## 4. Scope, measured

On a Starter tenant:

| | Count |
|---|--:|
| Blocked modules | 35 |
| Doctypes in them | 515 |
| Permission rows across all roles | 899 |
| **Rows held by roles a tenant user actually has** | **200** |
| Custom DocPerm rows already on the site | 354 |

The 200 is the number that matters. We do not need to touch 899 rows across 43
roles — most of those roles are never granted to anyone on a tenant. Restricting
the change to roles that are actually held keeps the blast radius small and the
reversal cheap.

---

## 5. What gets exempted, and why

| Who | Keeps access | Reason |
|---|---|---|
| `Administrator` | everything | Frappe bypasses permission checks for it entirely |
| `System Manager` | everything | the tenant's own admin sets up integrations, print formats, email |
| The control plane | untouched | `sync_site` already refuses to run there |

This is the same exemption module blocking already uses, so the product behaves
consistently: a tenant admin sees more than their staff, deliberately.

---

## 6. Delivery

| Step | What | Risk |
|---|---|---|
| 4a | `blocked_doctypes(features)` in the registry, derived from blocked modules | none — pure function, testable |
| 4b | `sync_permissions()` writing Custom DocPerm for those doctypes | **high** |
| 4c | Reversal — delete rows, `reset_perms`, verified by upgrading a real tenant | high |
| 4d | Withhold feature-specific roles (`Interviewer`) at user creation | low |
| 4e | Stop the setup wizard granting 44 roles to a customer account | medium |

4e is worth calling out separately: provisioning passes a real staff email to
ERPNext's setup wizard, which grants that user *every default role* — including
`Accounts Manager`, `Sales Manager`, `Stock Manager` and `Workspace Manager`.
Measured: 44 roles on a tenant that bought none of those modules. That is a live
over-permission today, independent of everything else here.

---

## 7. The risks, stated plainly

**This is the first change that can stop a paying customer working.** Everything
before it only affected what was drawn on screen.

| Risk | Mitigation |
|---|---|
| A doctype Frappe HR needs sits in a "blocked" module | Derive the list, then diff it against what an HR user touches in the existing test suite before applying |
| Custom DocPerm wipes standard perms for that doctype | Only ever write rows for doctypes we intend to restrict, and assert the exempt roles survive |
| An upgrade fails to restore access | Reversal tested first, on a real tenant, before the forward path ships |
| Existing tenants | Applied per site by `sync_site`, same as every other lever |
| A tenant admin locks themselves out | `System Manager` is exempt, and `Administrator` bypasses permissions entirely |

**Order of work:** build the reversal before the restriction. A change that can
deny access should not ship until putting it back is proven.

---

## 8. Waves 5 and 6, for completeness

Small, low risk, and worth doing alongside:

- **Wave 5** — install `alvoraa_goals` only when Goals is sold. `required_apps()`
  already computes it; provisioning ignores it. This is the only *real* denial we
  have today, since absent doctypes cannot be reached at all.
- **Wave 6** — gate the portal's own panels on `has_feature()`. The registry
  function exists and **nothing calls it**: the portal shows Goals, Analytics and
  the Vendor panel regardless of plan.

---

## 9. What I need

Approval for section 6, and a decision on one thing:

**How far should denial go?** Two options:

- **Read-only** — a blocked module's doctypes become unreadable. Cleanest, and
  matches "not accessible to anyone".
- **Hidden but usable by integrations** — strip `read` from the UI roles but keep
  API access for a tenant's own integrations.

I recommend the first. The second sounds accommodating but leaves the product in
the same half-gated state we have been fighting all day.
