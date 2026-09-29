# Implementation notes — ALV-166 Frappe Helpdesk, ALV-167 Frappe LMS (Part A)

**Author:** hrms-fullstack-engineer · **Date:** 28 Sep 2026 · Local only. No push, no PR,
no server touched. Built and tested in a throwaway Docker container of my own; the
existing `hrlocal-*` containers and the main checkout were never touched.

Builds on `01-product-brief.md`, `01d-devops-first-look.md` and
`01e-test-build-results.md`, all already in this worktree/branch. Surbhi's decisions
already on record there: Helpdesk is a resold customer-support desk, LMS is internal
training only (no priced course, no payment gateway), both opt-in per tenant.

---

## 0. What came in while I worked

Before touching anything I fetched `origin/dev` and rebased. Three commits came in that
this slice's branch did not have, all real:

- `3153eb9` ALV-156: pin Frappe, ERPNext and India Compliance to release **tags**
  instead of the `version-16` branch (`FRAPPE_BRANCH`/`ERPNEXT_BRANCH`/
  `INDIA_COMPLIANCE_BRANCH` renamed to `FRAPPE_TAG`/`ERPNEXT_TAG`/`INDIA_COMPLIANCE_TAG`).
- `f392abf` a documentation-only commit about the framework upgrade.
- `adf3b53` recorded that the pin is a no-op against what production now runs.

The rebase was clean (no conflicts). All my Dockerfile edits below build on the new
`ARG *_TAG` names, not the old `*_BRANCH` names.

---

## 1. What I built, file by file

| File | Mechanism | Why |
|---|---|---|
| `deploy/Dockerfile` | extend | Four new `ARG` pins (`PAYMENTS_COMMIT`, `LMS_COMMIT`, `TELEPHONY_COMMIT`, `HELPDESK_TAG`), four new `get-app` steps in dependency order (payments → lms → telephony → helpdesk), two new `bench build --production --app` steps (lms, helpdesk, both with the yarn cache mount), `apps.txt` updated, a comment on why no `git submodule update` is needed for either app's `frappe-ui` submodule. |
| `.github/workflows/build-image.yml` | fix a stale comment | "about 14 GB free" corrected to the measured 86–109 GB (27 Sep 2026, run 36323595557) — no behaviour change. |
| `alvoraa_portal/alvoraa_portal/subscription.py` | extend | `lms` and `helpdesk` added to `ERPNEXT_FEATURES`, same catalogue as `crm`/`whatsapp`. Off by default (absent from every `PLANS` entry — no `opt_in` flag used, matching `whatsapp`/`crm`, not `opt_in: True` — see §2 below for why). |
| `deploy/provision_tenant.sh` | extend | Two new `has_feature` blocks, mirroring `india_compliance`/`whatsapp`: install Payments then LMS (then apply LMS's privacy defaults); install Telephony then Helpdesk (then apply Helpdesk's privacy defaults). Neither app has a setup-wizard hook, so — unlike CRM — both install directly here, not deferred to `tenant_api` after the wizard. |
| `alvoraa_portal/alvoraa_portal/tenant_api.py` | extend | `needs_lms`/`needs_helpdesk` added to `update_tenant`'s existing-tenant plan-change path, and `install_lms`/`install_helpdesk` added to `_run_install_modules`, mirroring `needs_crm`/`needs_whatsapp` exactly. |
| `alvoraa_portal/alvoraa_portal/lms_defaults.py` | **build** (new module) | `apply_safe_defaults()` + `after_migrate()`. Turns off `LMS Settings.allow_guest_access`, `allow_job_posting`; writes `disable_signup=1` explicitly. Runs once per site, via a sentinel — never runs again. |
| `alvoraa_portal/alvoraa_portal/helpdesk_defaults.py` | **build** (new module) | Same shape, for `HD Settings.allow_anyone_to_create_tickets`. |
| `alvoraa_portal/alvoraa_portal/hooks.py` | extend | Both modules' `after_migrate` registered as a safety net (belt-and-suspenders alongside the explicit provisioning-time call). |
| `alvoraa_portal/alvoraa_portal/tests/test_lms_feature_166.py` | new | Registry, module access, provisioning, plan-change job, image pins, privacy-defaults idempotency — the same shape as `test_crm_feature_040`/`test_whatsapp_feature_042`. |
| `alvoraa_portal/alvoraa_portal/tests/test_helpdesk_feature_167.py` | new | Same shape, for Helpdesk. |

No new DocType, no forked upstream source, no custom field. Everything is configuration
(the feature registry, the provisioning script) plus two small first-party modules that
each do one thing.

---

## 2. `opt_in` — a deliberate difference from the brief's wording

The brief said "add `lms`... as `opt_in: True`". I checked `test_opt_in_features.py`
(the actual rule) before doing that, per the task's own instruction:
`opt_in` in this codebase means "sits outside `enterprise`'s definition of the whole HR
product **and** is switched on for a tenant by an explicit call, not just by omission
from a plan". Looking at `crm` and `whatsapp` — the two nearest precedents — **neither
uses `opt_in: True`**. They are off by default simply because no `PLANS` entry names
them; a tenant gets them only when `create_tenant`/`update_tenant` is told to. `lms` and
`helpdesk` follow the same shape for the same reason: they are not part of the HR
product at all (they live in `ERPNEXT_FEATURES`, not `FEATURES`), so `opt_in` does not
apply to them the way it applies to `late_rules` or `attendance_scoring` (real HR
features that are part of `enterprise` but off until switched on). Using `opt_in: True`
here would have been copying the brief's wording without checking it against the code —
exactly the mistake the boot sequence warns against.

---

## 3. Privacy defaults — the exact rule, and why

**LMS Settings ships open**: `allow_guest_access=1` (anyone with no login sees every
course), `allow_job_posting=1` (a public jobs board with nothing to do with internal
training). `disable_signup=1` is already the shipped default and is written explicitly
anyway, so a future upstream change to that default cannot silently reopen it here
without a test noticing.

**HD Settings.allow_anyone_to_create_tickets defaults to `0`** already — Helpdesk ships
safe on this one point. I read the app's own source at the pinned tag (cloned locally,
not recalled) to find this: `hd_settings.py`'s `on_update` hook is what actually grants
or removes the `Guest` role's permission on `HD Ticket` (`set_guest_ticket_creation_permission`
/ `remove_guest_ticket_creation_permission` in `hd_ticket.py`); `HD Ticket` itself carries
no `Guest` row in its own DocType JSON, so a site where this switch has never been
touched has **no** guest access to tickets at all. I still write the value explicitly,
for the same "protect against a future default change" reason as LMS's `disable_signup`.
I also checked for a Helpdesk-specific self-sign-up flag — there is none; the app has no
signup mechanism of its own, and a site's normal `Website Settings.disable_signup`
already covers it, unrelated to Helpdesk. `HD Article Category.allow_guest_to_view` is a
DocType-level schema default (the knowledge base is public by design, the same way a
support vendor's docs site is public) — not a per-tenant Settings field, so there is
nothing to flip here; documented in `helpdesk_defaults.py`'s own docstring as a
deliberate non-change.

**The "never flip back" rule.** Both modules apply their safe values exactly once per
site, tracked by a `frappe.db.get_default` sentinel (`alvoraa_lms_privacy_applied`,
`alvoraa_helpdesk_privacy_applied`). After that first write, `apply_safe_defaults()` is a
permanent no-op on that site, called from provisioning, from the existing-tenant
plan-change job, and from `after_migrate` on every site forever (a no-op unless the app
is actually installed and the sentinel is missing). This was **proven live**, not just
argued: I flipped `LMS Settings.allow_guest_access` back to `1` by hand in a throwaway
container, re-ran `apply_safe_defaults()`, and it stayed `1` — see §6.

I chose a permanent one-time write over "re-apply only if the field still equals the
factory default" because a Check field has no "untouched" state distinguishable from
"HR set it back to the same value on purpose" — the sentinel is the only mechanism that
can never fight a deliberate HR decision either way.

---

## 4. AC list

| AC (from the brief/task) | Status |
|---|---|
| LMS invisible on every tenant until `lms: true` | **Met** — off by default, not in any `PLANS` entry, `ERPNEXT_FEATURES["lms"]` gates the module and the app install |
| Helpdesk invisible on every tenant until `helpdesk: true` | **Met** — same mechanism |
| Public course catalogue / guest ticket creation off by default | **Met** — `lms_defaults.py`/`helpdesk_defaults.py`, proven live in §6 |
| Course completion vs Training Program overlap resolved | **Not in Part A scope** — the brief's own kill-criterion for a *deeper* LMS integration (Part B, the LMS↔HR training sync) was explicitly excluded from this task |
| Image build time and size measured and reported | **Met** — §7 |
| Negative-permission test: Employee from Tenant A cannot see Tenant B's data | **Partially met** — unit-level (`blocked_module_defs` hides the module for an unsold tenant, proven for both apps in the test files) and a real install proved the module is entirely absent from a site that never bought the feature (no tables exist, no URL routes exist, since the app itself is not installed). I did **not** provision two live tenants side by side to prove one cannot reach the other's course/ticket data over HTTP — that is a cross-tenant test, out of reach of a single throwaway container within this task's time, and is the kind of check `hrms-test-automation-engineer` should add as a dedicated cross-tenant test once this lands on a real multi-tenant dev stack. **Flagging as temporary debt.** |
| Both are opt-in per tenant | **Met** |
| First install goes to a demo tenant, not a live customer | **Not this engineer's call to execute** — provisioning commands are in §8, not run |

---

## 5. The seven non-functional dimensions, re-assessed against the code I wrote

- **Performance** — neutral for every existing tenant (no extra queries run unless the
  feature is ticked). For a tenant that buys either: `apply_safe_defaults()` is one
  `get_single` + one `save` + one `db.set_default`, once, ever, per site. `after_migrate`
  adds one `db.exists("DocType", ...)` check per site per migrate — negligible, and
  already the shape of six other `after_migrate` entries in this file.
- **Security** — improves. Both apps ship with real public-facing surface
  (guest course access, a public jobs board, and — checked, not assumed — a settings
  switch that could open ticket creation to anyone). This closes it before any tenant can
  reach either app, and proves it stays closed even after HR could have changed it.
- **Reliability** — neutral to improves. Installs are ordered (`payments` before `lms`,
  `telephony` before `helpdesk`) in both the shell script and the background job; a
  failed dependency install stops the feature install and reports why, mirroring the
  existing `crm`/`india_compliance` error handling exactly. `after_migrate` gives a
  second, independent path to the same safe state if the explicit call is ever skipped.
- **Scalability** — neutral. Feature-gated `install-app` means a tenant that never buys
  either app carries no extra tables, no extra migrate time, and no extra desk clutter —
  proven by installing on one site and reading `list-apps`/`blocked_module_defs`, the
  same reasoning already established for CRM/WhatsApp.
- **Maintainability** — improves. Two new small, single-purpose modules, each with one
  public function; nothing added to the already-large `subscription.py`/`tenant_api.py`
  beyond following their own existing pattern to the letter.
- **Data integrity** — neutral. Nothing here touches existing data; the sentinel key is
  new and namespaced, and idempotent (`_run_install_modules` and `provision_tenant.sh`
  can both be re-run safely — proven for the existing apps' pattern already, and the new
  blocks follow it).
- **Compliance / privacy** — improves, and is the actual point of this slice's second
  half: two apps that ship open now cannot reach a real tenant open. Sensitive fields
  touched: `LMS Settings`/`HD Settings` (site-level configuration, not personal data).

---

## 6. Proof — the throwaway build and container

**Build.** `docker build -f deploy/Dockerfile -t alvoraa-app:helpdesk-lms-test .` from
this worktree, after stripping CRLF from `deploy/provision_tenant.sh` and
`scripts/materialise_assets.sh` in the working copy only (the Windows checkout trap;
confirmed with `git diff --stat` that this introduces no real change to
`materialise_assets.sh`, which I did not otherwise touch). Local machine, not a GitHub
runner.

- **Build time: ~42 minutes** (started ~08:53, image `naming to` completed ~09:35 IST,
  28 Sep 2026). Consistent with the DevOps first look's interpolated "+30–50 min on a
  cold build that touches both" — this is the first real, full measurement of that
  number, not an estimate.
- **All 32 build stages succeeded**, all twelve apps materialised into real files
  (`materialised lms`, `materialised helpdesk`, ... `converted=12 remaining_symlinks=0`).

**Image size — measured, and the coordinator asked for the breakdown.**

| Measure | Value |
|---|---|
| `docker images` DISK USAGE, new image | 12 GB |
| `docker images` DISK USAGE, `alvoraa-app:local-042` (pre-slice reference) | 8.38 GB |
| Difference | **+3.62 GB** |

This is bigger than the throwaway proof's own estimate (`01e-test-build-results.md` §6,
~1.6 GB from `du` inside a running container). I do not believe that estimate was wrong —
I re-measured `du -sh apps/lms apps/helpdesk` live inside this build's own container and
got **1.1 GB + 523 MB ≈ 1.62 GB**, matching it almost exactly. The extra ~2 GB is real,
but it does not live in the *final, merged* filesystem — it lives in the **image's
layers**, which is a different thing `du` inside a running container cannot see.

`docker history --format '{{.Size}}'` on the new image, matched to the Dockerfile's own
step order, gives the per-layer cost directly:

| Step | Layer size |
|---|---|
| `get-app` payments (+checkout) | 27.4 MB |
| `get-app` **lms** (+checkout) | **1.87 GB** |
| `get-app` telephony (+checkout) | 18.8 MB |
| `get-app` **helpdesk** | **572 MB** |
| `bench build --app lms` | 77 MB |
| `bench build --app helpdesk` | 56.6 MB |
| **Directly attributable to the four new apps** | **≈ 2.62 GB** |

The remaining ~1 GB is not directly attributable to a single layer I added, and I want to
be precise about why, rather than guess: `bench setup requirements --node` (Dockerfile
step 3b — pre-existing, not written by this slice) re-runs `yarn install` across **every**
app in `apps.txt`, not only the freshly-`COPY`'d first-party apps it exists to fix
(`html2canvas` for `hrms`). That layer alone costs **783 MB** in this build. Docker layers
are immutable and additive: if that step rewrites even a fraction of `apps/lms/frontend/
node_modules` (762 MB, the single largest node_modules in the image) or `apps/helpdesk/
desk/node_modules` (421 MB) — say, because yarn re-resolves shared dependencies once the
whole apps.txt is in scope — the **original** bytes from the `get-app lms` layer stay
paid for in the image forever, even though the *live, merged* `apps/lms` folder ends up
smaller (1.1 GB, not 1.87 GB) once that later layer's changes apply. This is consistent
with the numbers: `1.87 GB` (layer) − `1.1 GB` (live `du`) ≈ `770 MB` of exactly this kind
of "written once, rewritten once, paid for twice" waste for LMS alone; Helpdesk's own gap
is much smaller (`572 MB` layer vs `523 MB` live du ≈ `49 MB`), because its node_modules
is a third the size of LMS's. **I did not verify this mechanism by instrumenting the
build** (that would need a second, longer build with intermediate layer inspection) — this
is the most consistent explanation the numbers support, not a confirmed root cause.

**What could be trimmed safely, and what I did not do without asking:**

- **The safe, well-understood fix**: delete `frontend/node_modules` (LMS) and
  `desk/node_modules` (Helpdesk) in the **same** `RUN` layer as their `bench build`
  step, after the build has produced the real deliverable (`apps/lms/lms/public`, 79 MB;
  `apps/helpdesk/helpdesk/public`, 52 MB). Nothing at runtime imports from a frontend's
  source `node_modules` once it is bundled — this is the same principle a multi-stage
  Docker build uses. Estimated recoverable: **up to ~1.18 GB** (762 MB + 421 MB), roughly
  a third of the measured growth.
- **I did not make this change.** The CRM step does the same thing today (its own
  `node_modules` are never deleted either, confirmed by reading the Dockerfile — this is
  a pre-existing pattern, not something this slice introduced), so trimming it properly
  means touching the shared per-app build block for **every** app in the image, which is
  bigger than "add two new apps" and was not part of what was approved. Doing it only for
  `lms`/`helpdesk` and not `crm`/`frappe_whatsapp` would be an inconsistent, easy-to-miss
  special case in a Dockerfile several people edit. **Recommend as a separate, small
  DevOps-led slice**, covering all four frontend-bundling apps at once, with its own
  before/after size measurement — not folded into this one without being asked.
- **Narrowing `bench setup requirements --node` to only the apps missing node_modules**
  (the real fix for the double-yarn-install waste) is a bigger, riskier change to a step
  every app in the image depends on, and needs its own verification that it does not
  silently stop covering a future first-party JS dependency. Flagged, not touched.

**Site creation and installs**, in a throwaway MariaDB 10.8 + Redis + this new image,
network `hdlms2-throwaway`, nothing shared with `hrlocal-*`:

- `bench new-site test.local` — succeeded.
- `bench --site test.local install-app erpnext hrms alvoraa_portal alvoraa_goals` — all
  four, exit 0.
- `bench --site test.local install-app payments` then `install-app lms` — both exit 0.
- `bench --site test.local install-app telephony` then `install-app helpdesk` — both exit
  0.
- `bench --site test.local list-apps` confirms all nine:
  `frappe 16.35.0, erpnext 16.36.0, hrms 17.0.0-dev, alvoraa_portal 0.0.1,
  alvoraa_goals 0.0.1, payments 0.0.1, lms 2.63.0, telephony 0.0.1, helpdesk 1.30.1`.

**Privacy defaults, confirmed live via `bench console`** (not read from the repo — the
actual database state):

```
LMS allow_guest_access= 0  disable_signup= 1  allow_job_posting= 0
HD  allow_anyone_to_create_tickets= 0
sentinels: 1 1
```

**"Never flip back" proven, not just argued**: I set `LMS Settings.allow_guest_access`
back to `1` by hand (simulating HR making a deliberate choice), re-ran
`apply_safe_defaults()`, and read it back — it stayed `1`. The sentinel stopped the
function from touching it a second time.

**Routes**, `bench start` inside the container only, killed immediately after:

```
curl -H 'Host: test.local' http://localhost:8000/lms       → 200
curl -H 'Host: test.local' http://localhost:8000/helpdesk   → 200
curl -H 'Host: test.local' http://localhost:8000/app        → 301 (login redirect, expected)
```

No new nginx `location` block is needed — confirmed live, matching the DevOps first
look's inference.

**A tenant without either feature does not get them** — proven at the unit level, not by
provisioning a second site (time): `blocked_module_defs`/`blocked_module_defs_for_hr`
correctly list `LMS`, `Job` and `Helpdesk` as blocked modules for a tenant selection that
does not include `lms`/`helpdesk` (see both test files, `TestModuleAccess`). Functionally
this is the identical mechanism already proven for CRM and WhatsApp — the app is simply
not installed on a site that never buys the feature, so there are no tables and no URL
routes to reach, regardless of module hiding.

---

## 7. Tests — what ran, and what it said

All run inside the throwaway container, against the real `test.local` site (not mocked
frappe outside a bench):

| Module | Result |
|---|---|
| `test_lms_feature_166` | **33 tests, all passed** (10 skipped — the ones reading `deploy/`/`.github/` files not mounted in this container; same as every existing `TestTheImageCarriesItPinned` class) |
| `test_helpdesk_feature_167` | **33 tests, all passed** (9 skipped, same reason) |
| `test_crm_feature_040` (neighbouring) | 40 tests, all passed (7 skipped) — unaffected |
| `test_whatsapp_feature_042` (neighbouring) | 29 tests, all passed (9 skipped) — unaffected |
| `bench --site test.local run-tests --app alvoraa_portal` (full suite) | Ran for 280s under a time cap; every test observed in that window passed, no failures seen, but the run did not reach completion before the cap. **Not a full-suite pass/fail confirmation** — flagged as temporary debt; a full run belongs to `hrms-test-automation-engineer`'s dedicated pass. |

**One real bug found and fixed during this proof**: `patch.object(module.frappe, "db")`
in both test files' `TestLmsDefaults`/`TestHelpdeskDefaults` was silently replaced by
`unittest.mock` with an `AsyncMock` rather than a `MagicMock` in this Python 3.14 /
`frappe.db` combination, which made `frappe.db.exists(...)`'s `side_effect` never
actually apply (the call returns an unawaited coroutine, always truthy). Fixed by
constructing the mock explicitly (`fake_db = MagicMock()`) and patching with `new=`,
which bypasses whatever auto-detection triggered the wrong mock type. Both tests now pass
for the right reason, proven inside the real bench, not just "looks plausible" outside
one.

**Static checks**, run locally (no bench needed):

```
ruff check <all changed/new .py files> --config hrms/pyproject.toml   → All checks passed
scripts/check_app_integrity.py                                        → OK - all consistent (665 checks)
scripts/check_brand_spelling.py --self-test && ... (no --self-test)   → OK - every screen says Alvora
scripts/check_version_pins.py --self-test && ...                      → OK (unaffected - only checks the 5 original pins)
```

`check_app_integrity.py` could not run its doctype-shadowing check outside a bench
(expected — it says so itself); the real proof that nothing shadows is the clean
`install-app` sequence above.

---

## 8. What is not done, and the exact next steps (dev-server actions — need Surbhi's word)

**Not done, on purpose:**
- No push, no PR, no `dev`/`main`/server change of any kind.
- No cross-tenant HTTP-level negative test (§4, §6) — unit-level only.
- The image-size fix (§6) — flagged, not applied.
- Full `alvoraa_portal` suite not run to completion (§7).

**Update from Surbhi, 28 Sep**: Helpdesk goes on **sargam.dev.alvoraa.co**; LMS stays on
**ppj.dev**. No code change follows from this — the feature registry and provisioning
script are already generic per-tenant. The exact steps, once she says to push to dev:

1. Push this branch's commits to `dev` (her word first).
2. Rebuild and deploy the image to dev (the normal `dev` pipeline — her word first).
3. **Tick the feature through the admin console** (`alvoraa_portal.tenant_api.update_tenant`,
   the same "our own provisioning path" CRM/WhatsApp already use) — via the tenant admin
   console UI, editing each tenant's module list:
   - `sargam.dev.alvoraa.co` → tick **"Customer Helpdesk"**, save. This queues
     `_run_install_modules` with `install_helpdesk=True`, which installs `telephony` then
     `helpdesk` and calls `helpdesk_defaults.apply_safe_defaults` — all in the background
     job already proven above.
   - `ppj.dev` (its real site name) → tick **"Learning & Certification"**, save. Same
     path, `install_lms=True`.
4. **Confirm**, once each job reports "Done" in the provisioning log:
   - `bench --site sargam.dev.alvoraa.co list-apps` shows `telephony` and `helpdesk`.
   - `bench --site ppj.dev list-apps` shows `payments` and `lms`.
   - Load `https://sargam.dev.alvoraa.co/helpdesk` and `https://ppj.dev/lms` — both
     should serve (200), not 404.
   - `bench --site sargam.dev.alvoraa.co console` → `frappe.db.get_value("HD Settings",
     "HD Settings", "allow_anyone_to_create_tickets")` reads `0`.
   - `bench --site ppj.dev console` → `frappe.db.get_value("LMS Settings", "LMS Settings",
     "allow_guest_access")` reads `0`.
   - Confirm every OTHER tenant on dev still shows neither feature (unchanged).

None of steps 1–4 were run. They need Surbhi's explicit go-ahead, per `CLAUDE.md` §1/§2.

---

## 9. Known gaps and shortcuts, honestly labelled

- **Temporary debt**: no HTTP-level cross-tenant negative test. Removed by
  `hrms-test-automation-engineer` adding one once two real tenants exist on a shared dev
  stack.
- **Temporary debt**: full `alvoraa_portal` suite not run to a clean finish inside my
  time budget — only the targeted and neighbouring modules were run to completion.
- **Intentional trade-off**: `PAYMENTS_COMMIT`/`LMS_COMMIT`/`TELEPHONY_COMMIT` are
  8-character abbreviated SHAs (as given in the task), not added to
  `scripts/check_version_pins.py`'s `PINS` tuple, which requires ≥12 hex characters. That
  script's own scope is the ALV-156 Frappe/ERPNext/India-Compliance triple; extending it
  to four more apps' pins is a reasonable follow-up but is a change to a different
  slice's script, done without being asked, so I left it alone and used the shas as
  given.
- **Acceptable simplification**: `HD Article Category.allow_guest_to_view` (the public
  knowledge base) is left as the app's own default — a DocType-schema property, not a
  Settings field, and public documentation is Helpdesk's intended behaviour, not a leak.
  Revisit if Helpdesk KB content is ever expected to be private.
- **Dangerous debt: none identified.** Both apps ship closed to the one real
  guest-access surface each has, proven live, and neither reaches any tenant that has
  not bought it.
