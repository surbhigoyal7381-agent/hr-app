# Slice 025 — The Alvoraa logo, for every tenant and every core screen

**Impact analysis and proposed strategy · 19 September 2026 · engineer**
**Status: waiting for the user's approval. No code written yet.**

Local only. Nothing is pushed. Nothing touches a server or a dev tenant.

---

## 1 · What is actually wrong

The user reported a broken-image icon on the portal. Three separate faults sit behind it,
and only the first was known.

| # | Fault | Evidence |
|---|---|---|
| 1 | **The logo is a private file.** `ppj.dev.alvoraa.co` has Website Settings `banner_image` = `/private/files/381140.jpg` and `favicon` = the same. A browser fetching `/private/files/...` does not carry Frappe's file permission check the way an API call does, so it renders as a broken image. | Diagnosed before this slice |
| 2 | **There is no product logo anywhere in the code.** `app_logo`, `brand_html` and `splash_image` are NULL on that tenant. No app ships an Alvoraa image. | `find alvoraa_portal -path "*public*"` returns one JS file and nothing else |
| 3 | **The portal's brand tile has been invisible the whole time.** `hrms-employee.html:140-146` sets the tile to `background:var(--surface)` *and* `color:var(--surface)` — the same token. The letter `{{ tenant_name[0] | upper }}` at line 2312 is therefore white text on a white tile in light mode, and dark-on-dark in dark mode. | `design_system.html:8` and `:15`; the two properties are literally the same variable |

So today an employee sees an empty rounded square in the sidebar, a broken image in the
navbar, and the **Frappe framework logo** in the desk (see §3).

---

## 2 · Where the assets can live, and what it costs

This bench serves `/assets/` in two different ways, and I checked both rather than assuming.

**Locally and in production, nginx serves `/assets/` straight off disk:**

```
deploy/nginx.conf:164   location ^~ /assets/ { alias /home/frappe/frappe-bench/sites/assets/; ... }
```

`sites/assets/alvoraa_portal/js/portal_switch.js` already resolves, so the path shape
`/assets/alvoraa_portal/images/<name>` is the right one. **But `sites/assets/alvoraa_portal`
is a real directory holding copies, not a symlink to the app.** I checked the inodes:

| Path | Size | Modified |
|---|---|---|
| `sites/assets/alvoraa_portal/js/portal_switch.js` (served) | 2,491 | 2026-09-10 |
| `apps/alvoraa_portal/.../public/js/portal_switch.js` (source) | 2,558 | 2026-09-05 |

Different sizes: the served copy is **already stale**. `deploy/Dockerfile:89-107` explains
why — `bench build` makes symlinks, then `scripts/materialise_assets.sh` turns them into
real files so nginx (which has no `/apps`) can follow them.

### The honest answer on the build step

**Yes, a build step is needed — and I am not running it without your word.**

| Environment | Does a new file in `public/images/` appear on its own? | Why |
|---|---|---|
| dev and production | **Yes, automatically** | Every push builds a new image, and `deploy/Dockerfile` runs `bench build` then `materialise_assets.sh` inside it. `migrate` is irrelevant to assets — the image already carries them. |
| the local bench `hrlocal-bench` | **No** | Its `sites/assets` is a baked copy in the `hrlocal-sites` volume. Nothing re-copies it. |

So for local proof I need **one** command, once, and it restarts nothing:

```
docker exec hrlocal-bench bench build --app alvoraa_portal   # then materialise_assets.sh
```

`bench build` is on the "never without asking" list, so **this is one of the two things I
am asking you for.** If you would rather not run it, say so — the tests below are written
so they prove the wiring without it, and the picture simply will not show on the local
bench until it runs.

### Why not the no-build alternative

Frappe also serves any binary file under `<app>/www/` directly through Python
(`frappe/website/page_renderers/static_page.py`), with no build step at all. I considered
putting the logo there. I am **not** proposing it, because that path goes through gunicorn
on every page load and gets no cache headers, while nginx serves `/assets/` with
`expires 30d; Cache-Control: public, immutable`. On the 3G phone budget (≤ 2.5 s p95,
`nfr-budget.md` §2) a cached, nginx-served mark is worth one build step. Saying so here so
the trade-off is yours, not mine.

---

## 3 · The desk logo — a trap worth naming before I build

The obvious mechanism is the `app_logo_url` hook, the way `hrms/hooks.py:8` does it.
**It does not work here.** Frappe resolves it like this
(`frappe/core/doctype/navbar_settings/navbar_settings.py:27`):

```python
logos = frappe.get_hooks("app_logo_url")
app_logo = logos[0]
if len(logos) == 2:
    app_logo = logos[1]
```

Three apps on this bench already declare it — frappe, erpnext and hrms — so `len(logos)`
is 3 and the winner is `logos[0]`, **the Frappe framework logo**. Adding a fourth changes
nothing. That is why the desk shows a Frappe logo today on any tenant where nobody set
Navbar Settings by hand.

So the desk logo has to be a **stored value**, and the resolution order is:

```
Website Settings.app_logo  →  Navbar Settings.app_logo  →  hooks (unusable)
```

I will write `Navbar Settings.app_logo`, which is the lowest rung a tenant can still
override from the UI. `hrms.subscription_utils.set_app_logo()` also writes that field, but
it is fenced behind `if not frappe.utils.get_url().endswith(".frappehr.com"): return`, so
it never fires for us. No conflict.

---

## 4 · The rule: tenant logo wins, Alvoraa fills the gap, nothing is ever broken

A tenant's own logo already has a home: `site_config.json` → `tenant_logo_url`, read by
`tenant_context.get_branding()` and written at provisioning by `tenant_api.py:911`.

**Proposed rule, one sentence:** *a tenant's own logo if it has one, otherwise the Alvoraa
mark, and never a broken image.*

Concretely, for each brand slot:

| Slot | Order |
|---|---|
| Portal sidebar mark | `tenant_logo_url` → Alvoraa mark asset → the tenant's initial letter (a real fallback again, once the invisible-colour bug is fixed) |
| Login page mark | same, rendered server side so there is no flash |
| Desk `app_logo`, `favicon`, `splash_image`, `banner_image` | whatever the tenant set → Alvoraa asset |

**How I tell a deliberate logo from the broken one** — this is the crux of the patch, so it
is explicit:

| Stored value | Verdict | Action |
|---|---|---|
| empty / NULL | nobody chose anything | set the Alvoraa asset |
| starts `/private/files/` | **the bug** — a browser can never render it | repoint to the Alvoraa asset |
| starts `/assets/alvoraa_portal/images/` | already ours | leave (or refresh the filename) |
| anything else — `/files/…`, an `http(s)://` URL, another app's asset | **a deliberate choice** | leave alone, untouched |

The middle row is the only repair. A tenant that uploaded a public logo keeps it. A tenant
that deliberately cleared a field... does get ours — I judge that acceptable for a field
that otherwise falls back to a Frappe logo, and I am flagging it rather than hiding it.

---

## 5 · Files I will change

| File | New/changed | Hot file? | Size of change |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/public/images/*.png` | new | no | 4 files |
| `alvoraa_portal/brand/alvoraa-logo-master.jpg` | new | no | the 1600×1600 master, **outside** `public/` so browsers never fetch 84 KB |
| `scripts/make_brand_assets.py` | new | no | regenerates the PNGs from the master |
| `alvoraa_portal/alvoraa_portal/brand.py` | new | no | the asset paths and the rule in §4, in one place |
| `alvoraa_portal/alvoraa_portal/tenant_context.py` | changed | no | two keys added to `get_branding()` |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` | changed | **yes** | ~8 lines: the brand tile at 2312 and its CSS at 140 |
| `alvoraa_portal/alvoraa_portal/www/alvoraa-login.html` | changed | no | the default mark at 367-377 |
| `alvoraa_portal/alvoraa_portal/hooks.py` | changed | **yes** | **one line appended** to `after_install` |
| `alvoraa_portal/alvoraa_portal/patches.txt` | changed | **yes** | **one line appended** |
| `alvoraa_portal/alvoraa_portal/patches/v1_0/repoint_broken_brand_images.py` | new | no | the repair |
| `alvoraa_portal/alvoraa_portal/tests/test_brand_logo_025.py` | new | no | the pin tests |
| `docs/slices/025-brand-logo/*` | new | no | notes |
| `docs/slices/009-ess-portal-redesign/09-brand-assets.md` | new | no | a pointer for the redesign |

**Not touching, on purpose:**

- `deploy/provision_tenant.sh` — it already runs `bench --site … install-app alvoraa_portal`
  (line 86), so `after_install` fires for every new tenant. Adding a line to the shell
  script would be a second, divergent copy of the same decision. **`after_install` is the
  honest place**, and it covers CI's `bench install-app` sites too.
- `tenant_api.py` — it only writes `tenant_logo_url` when the operator supplied one (line
  911). That is the tenant's own logo, which must keep winning. No change.
- `www/field-checkin.html` and `field_checkin.py` — the phone app **draws its own icon per
  request** in the tenant's colour (`field_checkin.py:975-1000`), deliberately, so a static
  file could never be one customer's. Slice 013 has also claimed these files. Leaving both
  alone.
- `goals-portal.html`, `vendor-portal.html`, `driver-portal.html` — I grepped them: none
  has any logo, mark or initials markup. They inherit the favicon from Website Settings, so
  fixing Website Settings fixes them with no edit.

---

## 6 · Parallel-work check

**What came in.** `git fetch origin` brought nothing new: `origin/dev` is still `baa9f68`.
Local `dev` is `3f5ce3d`, **two commits ahead and unpushed** — `99a17a4` "The bare address
lands where login does" and `3f5ce3d` "Make the landing tests survive a fresh site"
(slice 024, `auth.py`, `hooks.py`, `tests/test_home_page_024.py`). I branched from local
`dev`, so both are already under me.

**Other sessions' uncommitted work in the main checkout** — none of it mine, none of it
staged by me:
`.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`,
`docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`,
`hrms/.../alvoraa_position.py`, deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and untracked
`INDIA_PAYROLL_STRATEGY.md`, `OBJECTIVES_AND_KPI_SRS.md`, `SETUP-GUIDE.md`, `docs/legal/`,
`docs/priorities/`, `docs/slices/013-mobile-app/`, `docs/slices/_template/`,
`docs/slices/009-ess-portal-redesign/01b-ux-design.md`.

**Who else is in my files:**

| My file | Who else | Plan |
|---|---|---|
| `hrms-employee.html` | **010 fix round 2** holds it — review lists, `prOpenManagerReview`, HR finalize, flag buttons, calibration note box. **013 states "NEVER hrms-employee.html".** | **Split.** My change is the sidebar brand block (2312) and its CSS rule (140). Neither is in 010's list. I will not move, re-indent or rename anything else. |
| `hooks.py` | **013** holds it (`doctype_js`, HR Settings `doc_events`, appends to `after_migrate`/`after_install`). **024** added the `get_website_user_home_page` line at the top. | **Sequence-free append.** One line at the end of `after_install` with a comment, per the hot-file rule. On conflict, keep every entry from both sides. |
| `patches.txt` | **013** claims "append after 014's line". | **Append at the end only.** On conflict keep both lines in commit order. |
| `docs/slices/009-…/` | another session has `00-assessment-and-plan.md` modified and `01b-ux-design.md` untracked | I add a **new file** `09-brand-assets.md`. Different path, no clash. I do not edit their two. |
| `tenant_context.py`, `public/`, `tests/`, `brand.py`, `patches/v1_0/` | nobody on the board | free |

**The bench.** A run is live right now: `hrlocal-013` is running
`bench --site test_site run-tests --app alvoraa_portal` then `--app alvoraa_goals` for
slice 013, against `test_site`. **I will not start a test run until that one is finished**
and will re-check before I do. I will add my row to `.claude/work-in-progress.md` once you
approve.

**Other developers.** The board covers this machine only. Nobody else has touched
`hrms-employee.html`'s brand block or anything under `public/` in `origin/dev`'s last 7
days. **Do you know of anyone off this machine working on branding?**

---

## 7 · Verdict on the seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | **improves** | Today the navbar fetches `/private/files/381140.jpg` on every page, gets an error, and shows nothing — a wasted round trip. After: one ~3 KB PNG, nginx-served, `immutable`, cached 30 days, shared across every page and every tenant. No new query on any request path — the values are read from Website Settings, which Frappe already caches, and `get_branding()` reads `frappe.conf` (a dict in memory, zero queries). |
| **Security** | **improves** | It removes a case where a private file was linked into a public page. No new endpoint, no new input, no user-supplied path is used to select a file: the asset path is a constant in `brand.py`. The patch writes with `frappe.db.set_single_value` on two fixed Singles — no dynamic doctype, no string-formatted SQL. |
| **Reliability** | **improves** | Three layers: the tenant's logo, then the Alvoraa asset, then the initial letter. The `<img>` carries an `onerror` that removes itself so the letter shows through — **a missing file can no longer produce a broken-image icon**, which is the literal bug reported. The patch is safe to run twice. |
| **Scalability** | **neutral** | Nothing scales with headcount. One file, served by nginx, identical for all tenants. |
| **Maintainability** | **improves** | One module, `brand.py`, holds every path and the rule. One artwork file to replace (`alvoraa_portal/brand/alvoraa-logo-master.jpg`) plus one script to re-run — which answers the open ALVORA/ALVORAA question below without any code change. Today the rule lives nowhere and the letter fallback is silently broken. |
| **Data integrity** | **neutral, with one care point** | The patch writes to two Singles. The cache behind them is cleared in the same call (`frappe.clear_cache()` + `frappe.website.utils.clear_website_cache()`), which is what Frappe's own `WebsiteSettings.on_update` does — otherwise Guest would keep serving the old favicon until the next restart. That invalidation is part of this proposal, not a follow-up question. |
| **Compliance / privacy** | **improves** | No personal data is involved and none is logged — the patch logs the site name and the counts of fields changed, never a file name or a person. It also **narrows** exposure: a private-file URL sitting in a public page's HTML is removed. **No visibility is widened** — no field is added to any list view, export, notification or API response. |

**Personas.** CXO, HR Manager and Employee all see the same thing: the correct mark in the
rail, a real favicon on the tab, and the Alvoraa logo on the sign-in page. The HR Manager
additionally sees it in the desk navbar instead of the Frappe framework logo. No persona
gains or loses access to anything.

**Upgrade safety.** Everything lives in `alvoraa_portal` — an asset, a hook, a patch. No
edit to `apps/frappe`, `apps/erpnext` or `apps/hrms`. `bench update` cannot undo it.

**Accessibility.** The mark is decorative next to the tenant's name in text, so
`alt=""` plus the visible name is correct — a screen reader reads the name once, not twice.
The login page's mark gets `alt=""` for the same reason, with the product name already in
text beside it. Colour is not the only signal anywhere here. At 200 % zoom and 360 px the
mark scales with its tile because it is `object-fit: contain`, not a fixed bitmap size.

---

## 8 · Sizes and formats I propose

The master is 1600×1600 JPEG, 83,704 bytes, white background, wordmark **ALVORAA**, with
two distinct parts: an A-and-infinity monogram above, and the word below.

**PNG with transparency, not JPEG.** A JPEG carries its white box with it, and the portal
has a dark theme (`design_system.html:15`) — a white square would sit in the dark rail like
a sticker. The artwork is flat colour on flat white, so keying the white to alpha is safe;
I un-premultiply the anti-aliased edge pixels so the outline does not go grey.

| File | What it is | Size | Used by |
|---|---|---|---|
| `alvoraa-mark.png` | the monogram only, square, transparent | 128×128, target < 6 KB | sidebar rail (32 px, so 4× for retina), desk `app_logo` |
| `alvoraa-logo.png` | the full lockup, transparent | 512 wide, target < 14 KB | login page, `splash_image`, `banner_image` |
| `alvoraa-favicon.png` | the monogram, flattened on white | 32×32, target < 2 KB | browser tab |

Target total **under 22 KB**, fetched once and cached 30 days. `nfr-budget.md` sets no
explicit page-weight number; the binding target is the 3 G p95 of 2.5 s, and this is
comfortably inside it. I will report the real byte counts in the implementation notes
rather than these targets.

I will keep the master JPEG in the repo under `alvoraa_portal/brand/`, **not** under
`public/`, so it is version-controlled but never served.

---

## 9 · The tests, and how each is proved to fail without the fix

Per `parallel-work.md` §7, every one of these names the feature so a bad merge fails CI.
All are proved by switching the fix off in-process from a throwaway script on stdin —
no file is edited to break it.

| Test | What it pins | Fails without the fix because |
|---|---|---|
| `test_the_alvoraa_mark_resolves_for_a_fresh_site` | the asset exists at the path the pages reference, and the path is a real file inside the app | `public/images/` does not exist today |
| `test_a_tenant_with_its_own_logo_keeps_it` | `tenant_logo_url` set → `get_branding()` returns it, not ours | with the rule off, the Alvoraa mark overwrites the tenant's |
| `test_the_patch_repairs_a_private_file_path` | `favicon` = `/private/files/x.jpg` → becomes the asset path | with the patch off, it stays private and stays broken |
| `test_the_patch_leaves_a_deliberate_logo_alone` | `app_logo` = `/files/theirs.png` → unchanged after the patch | a naive "set it always" patch destroys a customer's logo — this is the test that stops that |
| `test_the_portal_never_renders_a_broken_image` | the rendered sidebar block contains no `/private/files/` and carries a visible fallback | today the tile renders an invisible letter and, on tenants like ppj, the navbar renders a private path |

The last one also pins the invisible-letter bug from §1 fault 3.

Proved on **`test_site` only**. No dev tenant, no server, no `docker cp`.

---

## 10 · How the redesign inherits this

Slice 009's prototype brands its rail the same shape this fix uses:

```js
// prototypes/009-ess-portal-redesign/prototype-v2.html:828
<div class="brand"><div class="mark">${TENANT.mark}</div>
  <div><div class="nm">${esc(TENANT.name)}</div><div class="sub">Alvoraa</div></div></div>
```

— a mark slot, the tenant's name, and "Alvoraa" as the sub-line. `appendix-a-frame.md`
FR-18 says "Tenant mark and name in rail … `get_branding()` … **Keep**". So the redesign is
already planning to call the same function. By putting the resolution in `get_branding()`
and the path in `brand.py`, the new frame gets it by calling what it already intends to
call, with nothing to reinvent. I will leave
`docs/slices/009-ess-portal-redesign/09-brand-assets.md` saying exactly that, with the
paths.

---

## 11 · Two things I need from you before I start

1. **ALVORA or ALVORAA?** The image you pasted in chat reads "ALVORA" (one A). The file on
   dev reads "ALVORAA" (two). I am building from the dev file, and the design deliberately
   makes this a one-file swap — drop the correct artwork in
   `alvoraa_portal/brand/alvoraa-logo-master.jpg`, re-run `scripts/make_brand_assets.py`,
   done. Nothing else changes. But I would rather ship the right word.
2. **May I run `bench build --app alvoraa_portal` on the local bench, once?** Without it the
   new file will not appear at `/assets/…` on `hrlocal-bench` (see §2). It writes only into
   the sites volume and restarts nothing, but it is on the never-without-asking list, and a
   test run for slice 013 is using the bench right now, so it would wait for that anyway.

**And the decision:** do you approve the strategy in §4, §5 and §8?
