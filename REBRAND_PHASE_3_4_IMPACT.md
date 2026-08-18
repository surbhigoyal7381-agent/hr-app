# Impact Analysis — Rebrand Phases 3 (Modules) & 4 (Apps)

**Status:** Impact analysis — Change Process step 1. No files renamed, no code changed.
**Date:** 2026-08-18
**Verdict:** 🔴 **Do not proceed yet.** Two blocking defects found, both pre-existing and both
independent of the rebrand. Renaming on top of them would bury them.

---

> **Historical record.** The names in this document are deliberately NOT updated to Alvoraa.
> It describes what past commits and past environments actually contained - `alvox_portal`,
> `Grace Cycle Config`, and so on. Rewriting them would make the record false. The final
> naming is Alvoraa everywhere; see `KPI_AUTOMATION_STRATEGY.md`.


## 1. Summary

Phase 3 and Phase 4 are mechanically small — 66 files, 44 module references, two `setup.py`
entries. That is not the risk.

The risk is that **a partial rename has already landed on `dev` and is internally inconsistent**,
and that **`grace_goals` contains two divergent copies of its core modules**. Both were found
during this analysis. Renaming now would carry both defects forward under new names, making them
substantially harder to diagnose.

---

## 2. Blocking finding 1 — the app rename is already half-done and does not resolve

The committed employee portal calls **28 API paths prefixed `alvox_portal.`**:

```
alvox_portal.goals_api.get_my_goals
alvox_portal.performance_api.get_company_values
alvox_portal.hr_api.get_pending_approvals
... 25 more
```

These are committed (`e480d32`), not working-tree edits. But:

| Check | Result |
|---|---|
| Does an `alvox_portal` Python package exist in the repo? | ❌ **No** — `find` returns nothing |
| `grace_vendor_portal/setup.py` | `name="grace_vendor_portal"` |
| `deploy/Dockerfile:45` | `COPY grace_vendor_portal apps/grace_vendor_portal` |
| `deploy/Dockerfile:52` | writes `grace_vendor_portal` into `sites/apps.txt` |
| `deploy/provision_tenant.sh:70` | `bench install-app grace_vendor_portal` |
| `.github/workflows/ci.yml:148` | `bench install-app grace_vendor_portal` |

The originating commit `4e580cd` is titled *"replace grace_vendor_portal API prefix with
alvox_portal (installed app name)"* — so the change was made on the belief that the installed app
is `alvox_portal`. Every build path in this repository installs it as `grace_vendor_portal`.

**Therefore one of these is true:**

- **(a)** Production runs an image built elsewhere, where the app genuinely is `alvox_portal` — in
  which case `deploy/` and `.github/` in this repo are stale and do not describe production; or
- **(b)** The goals, HR-approval and performance features of the employee portal are **currently
  broken** on any site provisioned from this repo, because `alvox_portal.goals_api.get_my_goals`
  cannot resolve.

I cannot distinguish (a) from (b) from the repository alone. **This must be resolved before any
further renaming** — it determines whether Phase 4 is a rename or a repair, and the two have very
different test plans.

> **Verification step (read-only, safe to run):**
> `bench --site <site> console` → `frappe.get_installed_apps()`
> Then `ls ~/frappe-bench/apps/` on the server. That answers it in ten seconds.

---

## 3. Blocking finding 2 — `grace_goals` has two divergent copies of its core modules

Both are tracked in git. Both differ substantially.

| Module | Shallow — `grace_goals/grace_goals/…` | Deep — `grace_goals/grace_goals/grace_goals/…` |
|---|---|---|
| `api/goal_api.py` | 127 lines | **314 lines** |
| `controllers/goal.py` | 132 lines | 163 lines |
| `controllers/evidence.py` | 131 lines | 101 lines |

**The shallow copy is the live one.** `hooks.py` references `grace_goals.controllers.goal`,
`grace_goals.permissions`, `grace_goals.scheduled_jobs` — all of which resolve to the package root,
i.e. the shallow path. The two frontend calls in `individual_goal.js` also use
`grace_goals.api.goal_api.*`.

**Nothing anywhere references `grace_goals.grace_goals.*`.** The deep `api/` and `controllers/`
directories are unreachable code.

That matters because the deep copy is the *newer* one. It contains functions the shallow copy does
not:

```
submit_kpi_progress      approve_kpi_progress
reject_kpi_progress      get_pending_approvals
_notify_manager          _auto_approve_enabled
```

These correspond to commit `95a0659` — *"KPI/Goal progress updates with evidence, approval
workflow, and manager notifications"*. So the KPI approval workflow appears to have been written
into a directory that Frappe never loads.

> **Note:** `grace_goals/grace_goals/grace_goals/doctype/` **is** correct Frappe layout — app /
> package / module / doctype. The anomaly is specifically the `api/` and `controllers/`
> directories duplicated *inside* the module directory. The doctype directory is fine and must
> stay where it is.

**Impact on the rebrand:** Phase 4 renames the package. If both copies are carried across, the
ambiguity survives under new names and the next person has the same puzzle with less history to
solve it from. Resolve which copy is authoritative, delete the other, **then** rename.

---

## 4. Phase 3 — Modules. Scope and impact

### 4.1 Scope

| Artefact | Count | Change |
|---|---|---|
| `"module": "Grace Goals"` in doctype JSON | **21** | → `Alvoraa Goals` |
| `"module": "Grace Vendor Portal"` in doctype JSON | **23** | → `Alvoraa Portal` |
| `modules.txt` | 2 files | One line each |
| Module directory names | 2 | Must match scrubbed module name |
| Workspace JSON | 1 (`grace_vendor_portal`) | Name + module |

### 4.2 Database impact

| Object | Effect |
|---|---|
| `tabModule Def` | 2 records renamed — **must be renamed, not deleted and recreated**, or every doctype orphans |
| `tabDocType.module` | 44 rows updated, in the same transaction as the Module Def rename |
| `tabWorkspace` | 1 record — referenced by name in navigation |
| Desk navigation / sidebar | Rebuilt from Module Def; stale cache shows the old name until `bench clear-cache` |

**No table renames.** Doctype names are untouched in Phase 3 — that was Phase 2. This makes Phase 3
materially safer than Phase 4.

### 4.3 Known trap

Commit `8f8216d` on the rebrand branch is titled *"Fix module directory names to match modules.txt
scrubbed names"* — the previous attempt renamed `modules.txt` but not the directories. Frappe
derives the module directory from the scrubbed module name, so a mismatch makes every doctype in
that module unloadable. **Rename `modules.txt`, the directory, and the 44 JSON `module` fields as
one atomic change.**

### 4.4 Rollback

Clean. Revert the commit, run `bench migrate` and `bench clear-cache`. The reverse patch renames
the Module Def back. No data loss path.

---

## 5. Phase 4 — Apps. Scope and impact

### 5.1 Scope

**66 files** contain `grace_goals` or `grace_vendor_portal`.

| Category | Count | Notes |
|---|---|---|
| Python import statements | **54** | Across both apps' controllers, tests, scheduled jobs, www pages |
| Frontend dotted API paths | **45** | In 13 files — `.js` and `www/*.html` |
| `hooks.py` handler paths | ~15 per app | `doc_events`, `permission_query_conditions`, `has_permission`, `scheduler_events` |
| `setup.py` | 2 | `name=` |
| `deploy/Dockerfile` | 4 lines | COPY, `pip -e`, `apps.txt` |
| `deploy/provision_tenant.sh` | 3 lines | install-app ordering |
| `.github/workflows/ci.yml` | 8 lines | ruff, cache key, copy, pip, apps.txt, install-app, run-tests |
| `.github/workflows/build-image.yml` | 1 line | comment |

### 5.2 The genuinely dangerous parts

**1. Frontend API paths are a runtime contract, not code.** 45 dotted paths are strings resolved at
call time. A missed one does not fail at build, at import, at `bench migrate`, or in any linter.
It fails when a user clicks a button in production. This is the single highest-risk element of
Phase 4, and it is exactly what blocking finding 1 already demonstrates.

**2. `installed_apps` is fragile in this project.** There is a documented history here: `bench
migrate` crashes unless the `installed_apps` global is populated in `tabDefaultValue`, and it must
be redone after site renames. An app rename touches precisely this, and the failure presents as an
unrelated migrate error.

**3. There is no `bench rename-app`.** The app must be uninstalled and reinstalled under the new
name, or `installed_apps` fixed by hand in both `tabDefaultValue` and `site_config.json`. Uninstall
carries a data-deletion risk if `--no-backup` or doctype cleanup flags are wrong.

**4. Install order matters.** `provision_tenant.sh` installs `grace_vendor_portal` *before*
`grace_goals`. Preserve that ordering under the new names — reversing it will fail on cross-app
doctype links.

**5. Cross-app coupling.** `grace_vendor_portal/www/hrms_employee.py`, `goals_portal.py`,
`performance_api.py` and `goals_api.py` all reach into goals data. The portal app is the *consumer*
of the goals app, so goals must be renamed and installed first, or the portal's imports break
mid-migration.

### 5.3 Rollback

**Not clean.** Reverting the code is easy; reverting `installed_apps` and the module registry on a
live site is not. Rollback = restore from backup. This is the phase that needs a rehearsed restore,
not just a taken backup.

---

## 6. NFR assessment

| Dimension | Phase 3 | Phase 4 |
|---|---|---|
| **Performance** | Neutral | Neutral |
| **Security** | Neutral | Neutral — but permission hooks (`permission_query_conditions`, `has_permission`) are dotted paths in `hooks.py`. **A missed rename here silently disables row-level scoping rather than erroring.** Must be explicitly tested, not assumed |
| **Reliability** | Low risk — no table renames | High — 45 runtime-resolved frontend paths with no build-time check |
| **Scalability** | Neutral | Neutral |
| **Maintainability** | Improves — consistent naming | Improves substantially, *if* findings 1 and 2 are resolved first; degrades if they are carried forward |
| **Data integrity** | Low risk | Medium — `installed_apps` corruption blocks migrate; uninstall/reinstall risks doctype data |
| **Compliance** | Neutral | Neutral |

The security row is the one I would not skip. `hooks.py` lines 29–35 map `Individual Goal` and
`KPI` to `grace_goals.permissions.*`. If those paths break, Frappe's behaviour on a missing
permission hook must be verified explicitly — a silent widening of visibility is far worse than a
crash.

---

## 7. Test plan

**Before (baseline capture):**
1. Record `frappe.get_installed_apps()` and `ls apps/` on each environment.
2. Export row counts for all 44 doctypes.
3. Screenshot/record the employee, manager and HR portal flows that currently work.

**After Phase 3:**
1. `bench migrate` + `bench clear-cache` clean on a scratch site.
2. All 44 doctypes open in Desk; module appears in sidebar under the new name.
3. Workspace loads.
4. Row counts unchanged.

**After Phase 4:**
1. `bench migrate` clean; `frappe.get_installed_apps()` shows only new names.
2. **All 45 frontend paths exercised by hand** — every button on the employee portal, manager
   portal, HR review and vendor/driver portals. This is not optional; nothing else catches them.
3. **Permission scoping verified as a non-privileged user**: an Employee sees only their own KPIs;
   a manager sees only their subtree. Confirms the permission hooks re-bound.
4. Scheduler events fire (`bench execute` each of the 3 scheduled jobs).
5. `bench run-tests --app <new name>` green for both apps.

---

## 8. Recommended order

| Step | Action | Risk | Gate |
|---|---|---|---|
| **A** | Resolve blocking finding 1 — confirm the real installed app name on each environment | None (read-only) | Answers rename vs repair |
| **B** | Resolve blocking finding 2 — decide which `grace_goals` copy is authoritative, delete the other, verify KPI approval workflow still works | Medium | Removes the ambiguity before it is renamed |
| **C** | Phase 0 CI branding check (whitelisting "Grace Period" / "Grace Group") | None | Catches misses automatically |
| **D** | **Phase 3** — modules, one atomic commit | Low–Medium | Soak on dev.alvoraa.co |
| **E** | **Phase 4** — apps, goals first then portal | High | Rehearsed restore; maintenance window |

Steps A and B are prerequisites, not optional preliminaries. A is free.

**Do not batch D and E into one deployment.** If something breaks you will not know which rename
caused it, and the diagnosis cost exceeds the deployment saving.

---

## 9. Go / no-go

🔴 **No-go on Phases 3 and 4 today.**

🟢 **Go on steps A, B and C now** — A is a read-only check, C is a CI addition with no runtime
effect, B is a cleanup that should happen regardless of whether the rebrand ever proceeds.

Blocking finding 1 in particular is worth acting on independently of the rebrand: if reading (b) is
correct, part of the employee portal is broken in production right now, and that is a more urgent
problem than what the app is called.

---

## 10. Questions

1. **What does `frappe.get_installed_apps()` return on production and on `dev.alvoraa.co`?**
   Everything in §2 depends on this.
2. **Which `grace_goals` copy is authoritative** — is the 314-line `goal_api.py` intended to be
   live, and is the KPI approval workflow currently reachable by users?
3. **Was `deploy/Dockerfile` used to build the running production image**, or was production built
   from `backup/dev-rebrand-aug-2026`?
4. Confirm target module names: `Alvoraa Goals` / `Alvoraa Portal` (brand) vs `Alvoraa Goals` /
   `Alvoraa Portal` (namespace-consistent). §2 of the rebrand plan assumed brand names for modules
   since they are user-visible in the Desk sidebar.
