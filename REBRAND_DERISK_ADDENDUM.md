# Rebrand De-Risking Addendum — Phases 3 & 4

**Status:** Investigation complete. Verdict revised.
**Date:** 2026-08-18
**Supersedes:** the no-go verdict in `REBRAND_PHASE_3_4_IMPACT.md` §9

---

> **Historical record.** The names in this document are deliberately NOT updated to Alvoraa.
> It describes what past commits and past environments actually contained - `alvox_portal`,
> `Grace Cycle Config`, and so on. Rewriting them would make the record false. The final
> naming is Alvoraa everywhere; see `KPI_AUTOMATION_STRATEGY.md`.


## 1. Verdict change: 🟢 proceed, with guard rails

The earlier no-go rested on two unknowns. Both are now resolved, and the answer inverts the risk
calculation: **delaying is worse than proceeding.**

| Earlier concern | Resolved to |
|---|---|
| The `alvox_portal` prefix may mean the portal is broken | It **is** broken today — 21 unresolved paths — and **the rename is the fix** |
| Two divergent `grace_goals` copies of unknown status | The deep `api/` + `controllers/` are provably **dead code**, safe to delete |
| Apps may be entangled, forcing one big-bang rename | **Zero cross-app imports at HEAD** — but a parallel session's uncommitted work adds portal → goals imports, so goals must be renamed first (see §4.3) |

---

## 2. Evidence

A new tool, `scripts/check_api_paths.py`, extracts every dotted API path from front-end assets and
resolves it against the Python tree — turning a runtime contract into a build-time check.

```
$ python scripts/check_api_paths.py                        # as-is
  total distinct paths : 219      UNRESOLVED : 23

$ python scripts/check_api_paths.py \
    --alias alvox_portal=grace_vendor_portal \
    --alias alvox_goals=grace_goals                        # simulated rename
  total distinct paths : 219      UNRESOLVED : 2
```

**21 of the 23 unresolved paths are fixed by performing the rename.** They are all
`alvox_portal.goals_api.*` / `hr_api.*` / `performance_api.*` calls in
`grace_vendor_portal/www/hrms-employee.html` — the employee portal.

The remaining 2 are pre-existing upstream HRMS paths
(`hrms.overrides.employee_payment_entry.*`), unrelated to branding and unaffected either way.

### 2.1 What this means

The front-end was already migrated to the new naming (commit `e480d32`, following `4e580cd`). The
back-end was not. Every affected call sits in one file, and each is a live user-facing feature:
goal creation, goal detail, check-ins, appraisal data, approvals, company values.

**The rebrand is not introducing risk here. It is discharging a debt that is already costing us.**

### 2.2 Correction

I flagged `performance_api.py` as possibly having a syntax error. It does not — the file carries a
UTF-8 BOM, my checker read it as plain UTF-8, and Python itself detects `utf-8-sig` and strips the
BOM on import. The script is fixed. The file is fine, though the BOM is worth removing for tidiness.

---

## 3. Dead code confirmed

`grace_goals` carries two copies of its core modules. Evidence that the deep copy is unreachable:

| Check | Result |
|---|---|
| `hooks.py` handler paths | All reference `grace_goals.controllers.*` / `.permissions` / `.scheduled_jobs` → **shallow** |
| Any reference to `grace_goals.grace_goals.*` | **None**, anywhere in the repo |
| Portal imports of `grace_goals` | **None** — apps fully decoupled |
| Front-end calls into `grace_goals` | 2, both `grace_goals.api.goal_api.*` → **shallow** |

So `grace_goals/grace_goals/grace_goals/api/` and `.../controllers/` are dead. The
`.../doctype/` directory beside them is correct Frappe layout and stays.

**One consequence worth surfacing:** `submit_kpi_progress` exists *only* in the dead copy. The
portal's progress submission goes through `goals_api.submit_goal_update` / `set_goal_progress`
instead. The KPI-progress function from commit `95a0659` was never reachable. Deleting it removes
nothing that runs — but confirm the intended workflow is the portal's before deleting.

---

## 4. De-risking mechanisms

### 4.1 The checker as a gate (built, working)

`scripts/check_api_paths.py` runs in under a second, needs no bench or database, and exits non-zero
on any unresolved path.

- **Before** each phase: capture the baseline count.
- **After** each phase: the count must be **≤ baseline**, never higher.
- **In CI:** add to `.github/workflows/ci.yml` so a missed rename fails the build instead of a
  user's click.

This is the guard that was missing in both previous rebrand attempts. It is the single highest-value
artefact from this investigation and is useful whether or not the rebrand proceeds.

### 4.2 Compatibility shim — makes Phase 4 non-breaking

Rename the package forward, then leave a thin shim under the **old** name:

```
grace_vendor_portal/grace_vendor_portal/goals_api.py
    from alvoraa_portal.goals_api import *        # noqa: F401,F403
```

Frappe resolves a whitelisted method by importing the dotted path and checking the resolved
function object against its whitelist registry. A re-exported function **is the same object**, so
it passes. Any path missed by the rename keeps working.

- Ship the shim with Phase 4.
- Remove it after one full soak cycle, gated on the checker reporting zero references to old names.
- This converts "a missed path breaks production" into "a missed path is caught by the checker at
  leisure".

### 4.3 Split Phase 4 into two deployments — goals first

At HEAD the apps have zero cross-app imports. **A parallel session's uncommitted work changes
that**, adding `from alvox_goals.permissions ...` and `from alvox_goals.controllers.kpi ...` to the
portal's `goals_api.py`, `hr_api.py` and `performance_api.py`. Once that lands the portal *depends
on* goals, so the order is no longer free: **goals must be renamed first, portal second.** That
happens to be the order recommended below anyway.

| Step | App | Blast radius | Rollback |
|---|---|---|---|
| 4a | `grace_goals` → `alvoraa_goals` | 2 front-end paths, desk hooks only | Revert + migrate |
| 4b | `grace_vendor_portal` → `alvoraa_portal` | 21 front-end paths, the whole portal | Revert + migrate (+ shim covers gaps) |

Do **4a first** — it is small, exercises the whole procedure (installed_apps, module registry,
migrate) on the low-value app, and proves the runbook before the portal is touched.

### 4.4 Delete dead code before renaming

Remove `grace_goals/grace_goals/grace_goals/api/` and `.../controllers/` **first**, as a separate
commit. Renaming 66 files is easier to review when ~600 lines of them are not duplicates. Verify
with the checker and a test run before and after.

### 4.5 Rehearsal on a scratch site

Phase 4's rollback is restore-from-backup, so the restore must be rehearsed, not merely available:

1. Clone production DB to a scratch site.
2. Run 4a end to end. Confirm `frappe.get_installed_apps()`, migrate, checker.
3. Deliberately break it (drop the `installed_apps` global) and practise the recovery.
4. Only then touch `dev.alvoraa.co`.

The `installed_apps` fragility has bitten this project before and presents as an unrelated migrate
crash. Rehearsing the recovery costs an hour and removes the worst production scenario.

---

## 5. Revised sequence

| # | Step | Risk | Reversible | Gate |
|---|---|---|---|---|
| 1 | Add checker to CI; record baseline (23) | None | Yes | — |
| 2 | Delete dead `grace_goals` api/controllers | Low | Yes | Checker unchanged; tests green |
| 3 | Confirm installed app names on each environment | None | — | `frappe.get_installed_apps()` |
| 4 | **Phase 3** — modules, one atomic commit | Low–Med | Yes | 44 doctypes load; workspace loads |
| 5 | Rehearse 4a on scratch site from a production clone | None | — | Runbook proven |
| 6 | **Phase 4a** — `grace_goals` → `alvoraa_goals` + shim | Medium | Yes | Checker ≤ baseline; desk hooks fire |
| 7 | Soak | — | — | One cycle |
| 8 | **Phase 4b** — `grace_vendor_portal` → `alvoraa_portal` + shim | Medium | Yes | **Checker drops 23 → 2** |
| 9 | Soak, then remove shims | Low | Yes | Checker reports zero old-name refs |

Step 8's exit criterion is objective and measurable: the unresolved count must fall from 23 to 2.
That is the moment the employee portal's goals features start working again.

---

## 6. Residual risks

| Risk | Mitigation | Residual |
|---|---|---|
| Missed front-end path | Checker + shim | **Low** — was the top risk, now double-covered |
| `installed_apps` corruption | Rehearsed recovery on scratch site | Low |
| Permission hooks silently unbind | Explicit non-privileged test: Employee sees own KPIs only, manager sees subtree only | **Medium** — no automated check; must be manual |
| Module Def renamed rather than recreated | Frappe patch, not SQL | Low |
| Doctype data loss on uninstall/reinstall | Verified backup before each step | Low |
| Conflicts with the 56-story KPI backlog | Do the rebrand **before** that work starts | Low if sequenced |

**The permission-hook risk is the one without an automated guard.** `hooks.py` binds
`Individual Goal` and `KPI` row-level scoping to `grace_goals.permissions.*`. If Frappe's behaviour
on an unresolvable permission hook is to skip it rather than raise, a missed rename widens
visibility silently. Test it as a real non-privileged user on the scratch site — do not infer it.

---

## 7. Recommendation

Proceed, in the order in §5. Two points worth holding to:

1. **Steps 1 and 2 first, today.** The CI check and the dead-code deletion carry no runtime risk,
   and both make everything after them easier to review.
2. **Do the rebrand before the KPI automation build starts.** Those 56 stories add files to exactly
   the packages being renamed. Renaming first is cheap; renaming mid-build is not.

The earlier no-go was right on the evidence then available. With the portal's 21 broken paths now
measured, the balance has shifted: **the rename is the repair.**
