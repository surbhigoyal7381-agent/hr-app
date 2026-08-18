# Rebrand Plan — Removing "Grace" from the Application

**Status:** Proposal — awaiting approval (Change Process step 2). No files renamed, no code changed.
**Date:** 2026-08-18
**Branch:** analysis performed on `dev`

---

## 1. Headline finding: this has already been done once

A complete four-phase rebrand exists on the branch **`backup/dev-rebrand-aug-2026`** (also
pushed to `origin`). It was never merged into `dev`.

| Commit | What it did |
|---|---|
| `e7566e8` | Phase 1 — Replace Grace/Kinexus branding with Alvox HRMS |
| `5720536` | Phase 2 — Rename `grace_vendor_portal` → `alvox_portal`, `grace_goals` → `alvox_goals` |
| `03a99df` | Phase 3 — Rename Grace DocTypes to Alvox, update module names |
| `b4b7752` | **Rebrand: Alvox HRMS → Alvoraa HRMS, alvox.in → alvoraa.co, purge remaining grace/kinexus strings** |
| `8f8216d` | Follow-up fix — module directory names did not match the scrubbed `modules.txt` |

Two follow-up fixes are the most valuable artefact here, because they record what the first
attempt got wrong: `8f8216d` (module dirs out of sync with `modules.txt`) and `4e580cd` on `dev`
(API prefix still using the old installed-app name). Both are exactly the class of breakage a
find-and-replace produces.

**The branch is stale.** `dev` and `backup/dev-rebrand-aug-2026` have diverged by
**28 commits on `dev`, 22 on the rebrand branch**, with a merge base at `184c5ea`. Everything
built since — leadership principles, rating-scale selectors, evidence workflow, KPI progress
updates, the past-objectives selector — landed on `dev` *after* the rebrand branch forked, and
touches precisely the files a rename would move.

**Recommendation: do not merge or cherry-pick that branch.** Re-execute the rename on current
`dev`, using the old branch as the *specification* — it tells us the agreed target names and the
traps — not as the change set.

---

## 2. Naming decision — DECIDED: Alvoraa everywhere

**Decision (2026-08-18): the target name is `Alvoraa`, for both the code namespace and the brand.
There is no Alvox waypoint.**

### 2.1 The history that made this look ambiguous

Commit `b4b7752` renamed **Alvox → Alvoraa**, and `CLAUDE.md` records the product as
"HR App (Alvoraa)" with the live domain `alvoraa.co`. But the *directory* names on that branch
stayed `alvox_goals` / `alvox_portal` even after the Alvoraa rebrand, which made it look as though
a deliberate split convention existed — namespace `alvox_*`, brand *Alvoraa*.

### 2.2 Why the split convention was dropped

Every argument for keeping `alvox_*` as the namespace turned out to be void:

| Apparent constraint | Reality |
|---|---|
| `alvox_compensation` already follows the convention | **Untracked, in no build path, zero doctypes.** A local scaffold — no constraint at all |
| 21 committed `alvox_portal.*` front-end calls would need rewriting | They are **already broken** and must be rewritten either way. Pointing them at `alvoraa_portal` costs nothing extra |
| Phase 3 was already built against Alvox | It was **uncommitted** — converting was a find/replace |

### 2.3 Why not Grace → Alvox → Alvoraa

The intermediate stop resolves nothing that going straight to Alvoraa does not, and it doubles
every database-touching step: the module patch, the doctype renames, the app rename (the single
riskiest step in the programme), and the production maintenance window. The Grace/Alvox split is
resolved by choosing the **final** name once, not by choosing the middle one.

### 2.4 Live constraint at time of decision

A parallel session is writing `from alvox_goals ...` imports into `goals_api.py`, `hr_api.py` and
`performance_api.py` (~16 lines, uncommitted). Those must be converted to `alvoraa_goals` and the
work coordinated, not overwritten. That work also introduces **cross-app imports (portal → goals)**,
which changes the Phase 4 ordering — see §6.

---

## 2A. Verified server state (2026-08-18) — the repo is BEHIND the servers

Checked directly on `dev.alvoraa.co`, read-only. This overturns the earlier assumption
that the deployed names matched the repo directories.

| Question | Answer on dev.alvoraa.co |
|---|---|
| Installed apps | `frappe, erpnext, hrms, **alvox_goals, alvox_portal**` |
| `Alvox Cycle Config` doctype | **exists** |
| `Alvox Rating Scale` doctype | **exists** |
| `Alvox Appraisal Extension` doctype | **exists** |
| `Goal Progress Update` doctype | **exists** |
| `Grace Cycle Config` / `Grace Rating Scale` / `Grace Appraisal Extension` | do **not** exist |

**Consequence:** the committed `alvox_portal.*` front-end calls and `Alvox *` doctype
references were **correct all along**. Phases 1–4 of the original rebrand were already
applied to the servers; only the repo *directories* still say `grace_*`.

So the remaining work is **Alvox → Alvoraa**, not Grace → Alvoraa. A "repair" that put
Grace back would have broken every server. It was written, dry-run, applied locally,
then reverted before any deployment once this check came back.

### 2A.1 The local container is not a reference

`kinexus.localhost` (local Docker) reports apps `grace_goals` / `grace_vendor_portal` and
is missing four doctypes. Its app code is **baked into the image and predates the repo**.
It is not a mirror of any server and must not be used to judge what is broken.

### 2A.2 Two defects found while checking

1. **`deploy/Dockerfile` does not describe any server.** It copies `grace_goals` /
   `grace_vendor_portal` and writes those into `sites/apps.txt`. Every server runs
   `alvox_goals` / `alvox_portal`. Whatever built the running image, it was not this file.
2. **`installed_apps` is duplicated on dev**: the list returns
   `['frappe','erpnext','hrms','alvox_goals','alvox_goals','alvox_portal','alvox_portal']`
   — every custom app twice. This is the known `installed_apps` fragility and should be
   cleaned before any app rename, which writes to that same list.

### 2A.3 One bench, four sites — "deploy to dev only" is not possible for code

`/home/frappe/frappe-bench/sites` on the server holds `alvoraa.co`, `dev.alvoraa.co`,
`minda.alvoraa.co` and `kinexus.alvoraa.co`. **App code is shared across all four**; only
the databases are separate. A `docker cp` into the backend container changes production
too. Any code rollout is therefore all-sites-at-once, and needs a different strategy than
a per-site copy.

---

## 3. Inventory — four kinds of "Grace", only two of them ours

This is the core of the analysis. **A blind find-and-replace would corrupt two of these four
categories.**

| # | Category | Files | Hits | Action |
|---|---|---|---|---|
| **A** | **"Grace Period"** — Frappe/HRMS attendance feature (late entry / early exit tolerance) | 46 | **306** | 🔴 **DO NOT TOUCH** |
| **B** | **"Grace Group" / "Grace Drinks"** — the customer's company name | 41 | **166** | 🔴 **DO NOT TOUCH** |
| **C** | **`grace_goals` / `grace_vendor_portal`** — app namespace | 64 | 277 | ✅ Rename |
| **D** | **`Grace *` DocTypes** — Cycle Config, Rating Scale, Rating Scale Item, Appraisal Extension | ~12 | ~13 | ✅ Rename |

### 3.1 Landmine A — "Grace Period"

172 occurrences of the literal string `Grace Period`, plus `grace_period` field names, inside
**upstream HRMS code we do not own**, including
`hrms/hrms/patches/v15_0/rename_enable_late_entry_early_exit_grace_period.py`.

Renaming these would break attendance processing and diverge our HRMS fork from upstream,
guaranteeing merge conflicts on every future pull. This is the single largest count of "Grace" in
the repository and **none of it is branding.**

### 3.2 Landmine B — "Grace Group" / "Grace Drinks"

The customer is *Grace Group*, an FMCG distribution business; the tenant is *Grace Drinks Pvt Ltd*.
These appear in:

- `hrms/hrms/grace_group/setup_grace_group.py` — customer-specific setup code
- Demo and seed data — company names, tenant names, employee records
- Documents — `Grace Group 2026.pdf`, `Grace_Group_Vendor_Portal_UseCase.md`, `Grace_global_logo.png`
- **Live production data** — Company records, Employee records, site names (`grace_localhost`)

Renaming these does not de-brand our product; it **falsifies customer records**. `Grace Group`
must remain `Grace Group` for the same reason a customer called Apple stays Apple.

> The one genuinely ambiguous item is `hrms/hrms/grace_group/` — customer-specific setup code
> living inside the product. It should move out of `hrms` into `demo/` or a tenant-config app, but
> that is a **separate refactor**, not part of the rebrand. Flagging, not scoping.

---

## 4. What actually changes

### 4.1 Apps (category C)

| Current | Target | Notes |
|---|---|---|
| `grace_goals/` | `alvoraa_goals/` | Dir, `app_name`, python package, all imports |
| `grace_vendor_portal/` | `alvoraa_portal/` | Note: **not** `alvoraa_vendor_portal` — the short form matches the existing front-end call shape |
| `alvox_compensation/` | `alvoraa_compensation/` | Untracked local scaffold, zero doctypes, in no build path — rename is free, no migration |

Per-app metadata in `hooks.py`:

| Field | Current | Target |
|---|---|---|
| `app_name` | `grace_goals` | `alvoraa_goals` |
| `app_title` | `Grace Goals` | `Alvoraa Goals` |
| `app_publisher` | `Grace Group` | `Alvoraa` |

`app_publisher` is currently the **customer's** name on our product. That is a licensing and
white-labelling problem independent of this rebrand, and worth fixing in the same pass.

### 4.2 Modules (category C)

`modules.txt` entries `Grace Goals` and `Grace Vendor Portal` → `Alvoraa Goals` / `Alvoraa Portal`.
Every doctype JSON carries `"module": "Grace Goals"` and must move with it. The module *directory*
name must match the scrubbed module name — this is precisely what `8f8216d` had to fix last time.

### 4.3 DocTypes (category D)

| Current | Target | Referencing files |
|---|---|---|
| `Grace Cycle Config` | `Alvoraa Cycle Config` | 3 |
| `Grace Rating Scale` | `Alvoraa Rating Scale` | 4 |
| `Grace Rating Scale Item` | `Alvoraa Rating Scale Item` | 2 |
| `Grace Appraisal Extension` | `Alvoraa Appraisal Extension` | 3 |

Blast radius in code is small. **Blast radius in the database is not** — see §5.

Note the proposed-but-unbuilt `Alvoraa Position` / `Alvoraa Position Assignment` from
`KPI_AUTOMATION_STRATEGY.md` §7. **Rename these in the strategy document now, before they are
built** — free today, a migration later.

### 4.4 Documentation and assets

`GRACE_USER_MANUAL.md`, `hrms/Grace_HRMS_Design_Theme_Guide.md`, `hrms/Grace_global_logo.png`,
`hrms/Grace_Group_Vendor_Portal_UseCase.md`, `hrms/Grace Group 2026.pdf`.

Split by category: the *design guide* and *user manual* are product docs (rename); the *vendor
portal use case* and the *2026 PDF* are customer documents (leave, or move to a customer folder).

---

## 5. The hard part: database migration

Renaming files is an afternoon. Renaming a **live** Frappe app is not, and production runs at
`alvoraa.co`.

### 5.1 Objects that live in the database, not in git

| Object | Where | Risk |
|---|---|---|
| Doctype tables `tabGrace Cycle Config` etc. | MariaDB | Table rename required |
| `tabDocType.module` = `Grace Goals` | MariaDB | Must update with module rename |
| `tabModule Def` records | MariaDB | Must be renamed, not recreated |
| `installed_apps` | `tabDefaultValue` + `site_config.json` | **Known fragility — see below** |
| Workspace `grace_vendor_portal` | MariaDB | Referenced by name |
| Custom Fields / Property Setters | MariaDB | `dt` column holds doctype names |
| Link field `options` | Doctype JSON **and** DB | Both sides must agree |
| Dynamic Link rows | Data | Store doctype names as *values* |
| Report / Dashboard / Notification refs | MariaDB | Silent breakage if missed |

### 5.2 The installed_apps trap

There is a documented, previously-hit failure in this project: **`bench migrate` crashes unless
the `installed_apps` global is populated in `tabDefaultValue`**, and it must be redone after any
site rename. An app rename touches exactly this. Budget for it explicitly — it has bitten this
project before and will present as an unrelated migrate failure.

### 5.3 Approach

Use Frappe's own machinery, not SQL:

1. `frappe.rename_doc("DocType", "Grace Cycle Config", "Alvoraa Cycle Config", force=True)` inside a
   **patch**, so it runs once per site and is recorded in `patches.txt`. Frappe renames the table
   and updates link references.
2. Module rename via a patch updating `tabModule Def` and `tabDocType.module` together.
3. App rename requires the app to be **uninstalled and reinstalled by its new name**, or a manual
   `installed_apps` fix-up. There is no clean `bench rename-app`. This is the riskiest single step.
4. Full backup before each phase; verified restore rehearsed on a scratch site *before* touching
   `dev.alvoraa.co`.

**Never** rename tables with raw SQL — link references and Dynamic Links will not follow.

---

## 6. Phased plan

Each phase is independently shippable and independently revertible.

| Phase | Scope | Risk | DB migration |
|---|---|---|---|
| **0 · Guard rails** | ✅ `scripts/check_api_paths.py` built and wired into CI at `--max 23`. ⬜ Still to write: `scripts/check_branding.py`, greping for banned strings **while whitelisting categories A and B** | None | No |
| **1 · Strings only** | `app_title` → `Alvoraa Goals` / `Alvoraa Portal`; `app_publisher` → `Alvoraa`; UI labels; docs. `Alvoraa Position*` already renamed in the strategy doc | Low | No |
| **2 · DocTypes** | 4 doctypes → `Alvoraa Cycle Config`, `Alvoraa Rating Scale`, `Alvoraa Rating Scale Item`, `Alvoraa Appraisal Extension`, via `rename_doc` patches | **High** | Yes |
| **3 · Modules** | ✅ **Code complete (uncommitted)** — `modules.txt`, module dirs → `alvoraa_goals` / `alvoraa_portal`, 44 doctype JSONs, workspace, `Module Def` patch per app | **High** | Yes |
| **4 · Apps** | `grace_goals` → `alvoraa_goals` **first**, then `grace_vendor_portal` → `alvoraa_portal`; imports, hooks, the 21 front-end paths, `installed_apps` | **Highest** | Yes |
| **5 · Verify** | CI branding check green; full E2E on all three personas; reconcile against `backup/dev-rebrand-aug-2026` for anything missed | — | No |

**Phase 0 is the highest-value step and costs almost nothing.** An automated check that
distinguishes "Grace Period" and "Grace Group" from `grace_goals` is what prevents this rebrand
being attempted a third time.

### Sequencing constraint

Phases 2–4 each require `bench migrate` on every site (local, `dev.alvoraa.co`, `minda.alvoraa.co`,
production). Run them in that order across environments, with a soak period between. Do **not**
batch phases 2–4 into one deployment — if it breaks, you will not know which rename did it.

---

## 7. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Find-and-replace hits "Grace Period" → attendance breaks, HRMS fork diverges from upstream | **Critical** | Category A whitelist in the CI check; never run an unscoped `sed` |
| Find-and-replace hits "Grace Group"/"Grace Drinks" → customer records falsified | **Critical** | Category B whitelist; review every diff hunk in demo/seed data |
| App rename corrupts `installed_apps`, `bench migrate` fails | **High** | Known issue with a known fix; rehearse on a scratch site |
| Doctype rename leaves stale Link `options` → silent data loss | **High** | Use `rename_doc`, never SQL; post-migration referential check |
| Production downtime on `alvoraa.co` | **High** | Phases 2–4 in a maintenance window; verified backup + rehearsed restore each time |
| Third rebrand attempt because scope was ambiguous | Medium | §2 decision recorded before Phase 1; CI check makes regression visible |
| Stale worktrees under `.claude/worktrees/` carry old names | Low | Prune before starting |

---

## 8. Recommendation

1. ✅ **Naming decided — Alvoraa everywhere** (§2). No Alvox waypoint.
2. ✅ **Phase 0 part one done** — `check_api_paths.py` is in CI and already measures the debt
   (23 unresolved, dropping to 2 when Phase 4 lands). The branding check remains to be written.
3. ✅ **Phase 3 code complete**, uncommitted, verified: `scrub(module) == directory` for both apps.
4. **Coordinate with the parallel session before it commits more `alvox_goals` imports** (§2.4).
   Every hour of delay adds churn to work that has to be converted anyway.
5. **Do Phase 1 (strings) next** — visible progress, no database risk.
6. **Then Phase 2 (doctypes), then Phase 4 (apps).** Phase 4 is goals-first because the parallel
   work makes the portal depend on goals.
7. **Do the whole rebrand before the KPI automation build starts.** Those 56 stories add files to
   exactly the packages being renamed. Renaming first is cheap; renaming mid-build is not.

The cheapest correct order is: name decided, guard automated, harmless strings, doctypes, modules,
apps — once, to the final name, before the next feature lands on top.

---

## 9. Open questions

1. ~~`alvox_*` namespace with *Alvoraa* branding?~~ **Resolved: Alvoraa everywhere** (§2).
2. ~~Does `alvox_compensation` get renamed?~~ **Yes — and it is free.** Untracked, no doctypes, in
   no build path.
3. **`app_publisher = "Grace Group"`** — should this become `Alvoraa`? It currently names the
   customer as the publisher of our product.
4. **`hrms/hrms/grace_group/setup_grace_group.py`** — leave as customer config, or move out of the
   HRMS fork? Recommend moving, but as a separate task.
5. **Site names** (`grace_localhost`, backup filenames) — in scope, or leave alone? Renaming a site
   re-triggers the `installed_apps` issue.
6. **Is `backup/dev-rebrand-aug-2026` safe to delete** once this plan supersedes it, or should it be
   kept as the reference specification? Recommend keeping until Phase 5 completes.
