# Slice 025 — implementation notes

**19 September 2026 · engineer · local only, nothing pushed**
Branch `slice/025-brand-logo`, worktree `.claude/worktrees/025-brand-logo`, from local
`dev` `3f5ce3d`. Strategy approved by the user on 19 September; `bench build` on the local
bench approved in the same message.

> **Read first: the artwork on disk is a PLACEHOLDER.**
> The user chose the spelling **ALVORA** (one A). The only file that exists is the one from
> the dev tenant, whose wordmark reads **ALVORAA** (two). Nothing was redrawn or retouched —
> a hand-made brand asset is worse than a placeholder.
> Because of that, **every slot that is actually displayed uses the monogram**, which has no
> lettering in it and is correct either way. See §4.

---

## 1 · The three faults, and the mechanism for each

The report was "the logo does not appear". Three independent faults were behind it, and
two of them were not known before this slice. They are listed separately because two are
bugs in their own right and would otherwise be lost inside a logo slice.

### Fault 1 — the logo was a private file

Website Settings on `ppj.dev.alvoraa.co` held `banner_image` and `favicon` =
`/private/files/381140.jpg`. A browser fetching `/private/files/...` does not carry
Frappe's file permission check the way an API call does, so the request is refused and the
page draws the broken-image icon. **The file was never missing. It was unreadable.**

*Mechanism: an app asset.* `alvoraa_portal/public/images/` is served by Frappe and nginx at
`/assets/alvoraa_portal/images/` — public by design, identical on every site, no upload, no
`docker cp`, nothing to copy when a tenant is created.

### Fault 2 — the portal's brand tile has been invisible since it was written

`hrms-employee.html`, the `.sidebar-brand-logo` rule:

```css
background: var(--surface);
color:      var(--surface);   /* the SAME token */
```

`--surface` is `#FFFFFF` in the light theme and `#221E1B` in the dark one
(`design_system.html:8` and `:15`). So `{{ tenant_name[0] | upper }}` has been white text on
a white tile, and dark on dark — **an empty rounded square in both themes.** Anyone who
believed there was a letter fallback was looking at nothing.

*Mechanism: `color: var(--primary)`.* `#5B4B8A` on `#FFFFFF` and `#A99AD4` on `#221E1B`;
both pass WCAG AA. Pinned by `test_the_brand_tile_letter_is_no_longer_invisible`, which
fails if the two properties ever name the same custom property again.

### Fault 3 — the desk logo cannot be set by a hook

The obvious mechanism is `app_logo_url` in `hooks.py`, the way `hrms/hooks.py:8` does it.
**It cannot work here.** `frappe/core/doctype/navbar_settings/navbar_settings.py`:

```python
logos = frappe.get_hooks("app_logo_url")
app_logo = logos[0]
if len(logos) == 2:
    app_logo = logos[1]
```

frappe, erpnext and hrms all declare it, so `len(logos)` is 3, the winner is `logos[0]` —
**the Frappe framework logo** — and a fourth declaration changes nothing. That is why any
tenant nobody configured by hand shows a Frappe logo in the desk today.

*Mechanism: a stored value.* `get_app_logo()` prefers
`Website Settings.app_logo` → `Navbar Settings.app_logo` → the hook. We write
**`Navbar Settings.app_logo`**, the lowest rung, so a tenant can still override us from
either settings form. Pinned by `test_the_desk_logo_cannot_be_left_to_the_hook`, which is
written to **fail** if the app count ever drops to two — at which point the hook starts
working and somebody gets to delete code.

---

## 2 · What was built, file by file

| File | New / changed | Mechanism | Why this one |
|---|---|---|---|
| `alvoraa_portal/brand/alvoraa-logo-master.jpg` | new | **configure** — artwork under version control | The single file to replace. **Outside `public/`** so a browser never fetches 84 KB to draw 32 pixels |
| `scripts/make_brand_assets.py` | new | **build** | Turns one master into the three served files. Finds the monogram and the lockup **by ink, not by hard-coded pixel numbers**, so a replacement master with different margins still works |
| `alvoraa_portal/public/images/alvoraa-mark.png` | new | app asset | the monogram, 128×128 |
| `alvoraa_portal/public/images/alvoraa-logo.png` | new | app asset | the full lockup, 320×187 — **built and ready, not displayed yet** (§4) |
| `alvoraa_portal/public/images/alvoraa-favicon.png` | new | app asset | 32×32, on white |
| `alvoraa_portal/alvoraa_portal/brand.py` | new | **build** — one module | The asset paths, the `SLOTS` table, and `_verdict()`, which is the whole judgement about whose logo wins. One place to read, one place to change |
| `alvoraa_portal/alvoraa_portal/tenant_context.py` | changed | **extend** | `get_branding()` gains `brand_mark_url` and `brand_logo_url`. The rule lives here because every branded page already calls this function and FR-18 says the redesign will keep calling it |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` | changed | **extend** | The mark in the rail, the invisible-letter fix, and the CSS that lets the letter show through a failed image. Two small regions: the rule at ~140 and the tile at ~2312 |
| `alvoraa_portal/alvoraa_portal/www/alvoraa-login.html` | changed | **extend** | The mark rendered **server side** instead of by JavaScript after first paint; a neutral tile ground; the placeholder SVG kept as the last resort |
| `alvoraa_portal/alvoraa_portal/hooks.py` | changed | **configure** — one line | `after_install` → `alvoraa_portal.brand.after_install`. **Nothing else in the file touched** |
| `alvoraa_portal/alvoraa_portal/patches.txt` | changed | one line, appended at the end | |
| `.../patches/v1_0/repoint_broken_brand_images.py` | new | **build** | The repair for sites already live |
| `.../tests/test_brand_logo_025.py` | new | tests | 12 tests, §6 |
| `docs/slices/009-ess-portal-redesign/09-brand-assets.md` | new | note | Where the assets are, and the two things the new frame must not lose |

**Deliberately not changed:**

- **`deploy/provision_tenant.sh`** — line 86 already runs
  `bench --site "$SITE_NAME" install-app alvoraa_portal`, so `after_install` fires for every
  new tenant. A line in the shell script would be a second, divergent copy of the same
  decision. `after_install` is the honest single place, and it also covers CI, which builds
  its site with `install-app` and nothing else.
- **`tenant_api.py`** — it writes `tenant_logo_url` only when the operator supplied a logo
  (line 911). That is the tenant's own logo and it must keep winning. Untouched.
- **`www/field-checkin.html`, `field_checkin.py`** — the phone app **draws its own icon per
  request** in the tenant's colour, with a contrast check against white
  (`field_checkin.py:975-1030`), because a static file could only ever be one customer's.
  That is a better answer than ours for that surface. Slice 013 has also claimed these
  files. Left alone.
- **`goals-portal.html`, `vendor-portal.html`, `driver-portal.html`** — grepped: no logo,
  mark or initials markup in any of them. They inherit the favicon from Website Settings, so
  the patch fixes them with no edit. All three already call `get_branding()`, which a test
  asserts.

---

## 3 · The rule, and how a deliberate logo is told from a broken one

**One sentence: a tenant's own logo if it has one, otherwise the Alvoraa mark, and never a
broken image.**

The tenant's own logo already had a home — `site_config.json` → `tenant_logo_url`, written
at provisioning, read by `get_branding()`. Nothing here overrides it.

`brand._verdict(value)` is the whole judgement:

| Stored value | Verdict | Action |
|---|---|---|
| empty, whitespace, or Frappe's `attach_files:` placeholder | `empty` | write ours |
| starts `/private/files/` | `broken` | write ours — **no browser can ever render this value**, so replacing it is always safe |
| starts `/assets/alvoraa_portal/images/` | `ours` | rewrite, so a renamed asset is picked up |
| anything else — `/files/…`, `http(s)://…`, another app's asset | **`None`** | **leave it exactly as it is** |

That last row is the one that matters. A patch that runs once across every live customer
and sets a logo unconditionally would delete their branding.
`test_the_patch_leaves_a_deliberate_logo_alone` is what stands between this code and that
outcome, and it covers both a `/files/` path and an external URL.

**Never a broken image**, concretely: the tile keeps the tenant's initial as text
*underneath* the image, and the image carries `onerror="this.remove()"`. If the asset 404s —
a missed build, a renamed file — the image takes itself out of the way and the letter shows.
The login page does the same and additionally puts its placeholder SVG back.

### Where each slot points

| Slot | Value | Who overrides |
|---|---|---|
| portal rail, login tile | `brand_mark_url` | the tenant's `tenant_logo_url` |
| `Website Settings.favicon` | the favicon asset | anything the tenant set |
| `Website Settings.app_logo`, `Navbar Settings.app_logo` | the monogram | anything the tenant set |
| `Website Settings.banner_image`, `splash_image` | **the monogram for now** — see §4 | anything the tenant set |

---

## 4 · The placeholder, and the one command that swaps it

The master reads **ALVORAA**. The chosen spelling is **ALVORA**. I did not redraw it.

The logo has two parts, and only one of them carries type:

| Asset | Carries lettering? | Displayed now? |
|---|---|---|
| `alvoraa-mark.png` — the A-and-infinity monogram | **no** | **yes.** It is correct whichever spelling wins |
| `alvoraa-favicon.png` — the same monogram, on white | **no** | **yes** |
| `alvoraa-logo.png` — the full lockup, monogram + wordmark | **yes, and it is wrong** | **no** |

So `banner_image` and `splash_image`, the two slots with room to read a wordmark, point at
the monogram for now. Showing a customer the wrong spelling of our own name is worse than
showing them a small mark. `brand_logo_url` is exposed for the redesign but **nothing
renders it**, and there is a comment in `tenant_context.py` saying why.

**Nothing visible is wrong today.** The slice does not need to be held.

### When her file lands

Save the artwork as `alvoraa_portal/brand/alvoraa-logo-master.png` (or `.jpg` / `.webp` —
the script takes any of them; a transparent PNG or a vector export is best), then:

```bash
cd C:/Surbhi-Git/hr-app                       # or the worktree
python scripts/make_brand_assets.py
```

It prints the three files with their real sizes. Then **one line** in `brand.py`: put `LOGO`
back in the `banner_image` and `splash_image` rows of `SLOTS`. Nothing else changes — not a
path, not a template, not a test. The old master should be deleted in the same commit, so
there is only ever one.

---

## 5 · Sizes, formats and the numbers behind them

The master is 1600×1600, 83,704 bytes, JPEG on white. Shipping it would be 84 KB to draw a
32-pixel tile.

| File | Size | Bytes | Format | Drawn at |
|---|---|---|---|---|
| `alvoraa-mark.png` | 128×128 | **2,064** | palette PNG, transparent | 32 px rail, 42 px login — 128 covers a 4× screen |
| `alvoraa-logo.png` | 320×187 | **8,170** | palette PNG, transparent | banner / splash, when the wordmark is settled |
| `alvoraa-favicon.png` | 32×32 | **1,146** | PNG on white | browser tab |
| | | **11,380 total** | | vs 83,704 for the master |

**PNG, not JPEG**, because a JPEG cannot hold transparency and so carries its white box into
the dark theme, where it would sit in the rail like a sticker. The artwork is flat colour on
flat white, so keying the white out is safe.

**Palette PNG, not full colour and not WebP.** Measured on this artwork at 320 px wide:

| Format | Bytes |
|---|---|
| full-colour PNG | 56,872 |
| WebP, quality 88 | 25,726 |
| **64-colour palette PNG** | **8,170** |

A smooth two-colour gradient is the worst case for full-colour PNG and about the best case
for a palette; lossy WebP spends its bytes on the alpha channel. 64 colours keeps **53
distinct alpha levels**, so the anti-aliased edge stays smooth — checked by compositing the
saved file onto the dark theme's background and looking at it at 4× zoom, not by trusting
the number.

**The white-keying is deliberately dull**: `alpha = distance from white in the darkest
channel, scaled so anything past 40/255 is fully opaque`. Solid artwork — even the pale
lilac at `(173,153,188)`, which is 102 from white — comes out completely opaque. Only real
edge pixels land in between, and those are un-premultiplied so the outline keeps its colour
instead of fading to grey on a dark ground.

`nfr-budget.md` sets no explicit page-weight number; the binding target is the employee 3G
p95 of 2.5 s (§2). 11 KB fetched once and then cached 30 days is comfortably inside it.

### Legibility check

Rendered at the actual drawn sizes — 32 px and 42 px — on `#FFFFFF` and on `#221E1B`, at 4×
zoom. The monogram reads as the A-and-infinity mark in all four. On the dark ground the A's
inner counter goes transparent and shows the dark background through it; the form still
reads because of the surrounding strokes, and that is the correct behaviour for a
transparent logo rather than a fault.

---

## 6 · The tests, and the fail-without-fix proof

`alvoraa_portal/alvoraa_portal/tests/test_brand_logo_025.py`, 12 tests in 4 classes.

| Test | Pins |
|---|---|
| `test_the_alvoraa_mark_resolves_for_a_fresh_site` | all three assets exist inside the app, at exactly the paths `brand.py` promises |
| `test_the_brand_assets_stay_small_enough_for_a_phone` | under 40 KB total — a guard against somebody dropping the master straight in |
| `test_the_master_artwork_is_not_served` | the 84 KB master never becomes a public asset, and no stray file appears in `public/images` |
| `test_a_tenant_with_its_own_logo_keeps_it` | `tenant_logo_url` wins over the Alvoraa mark |
| `test_a_tenant_with_no_logo_gets_the_alvoraa_mark` | the gap is filled |
| `test_the_tenants_own_setting_is_still_readable` | callers can still ask "did this tenant set a logo?" |
| `test_the_patch_repairs_a_private_file_path` | the reported bug, as a test |
| **`test_the_patch_leaves_a_deliberate_logo_alone`** | **a customer's own logo survives the patch** — `/files/…` and an external URL |
| `test_an_empty_slot_is_filled` | the desk logo stops being Frappe's |
| `test_the_desk_logo_cannot_be_left_to_the_hook` | the `logos[0]` trap, and fails the day it stops being true |
| `test_running_it_twice_changes_nothing_the_second_time` | safe to run twice |
| `test_the_portal_never_renders_a_broken_image` | the tile draws the resolved mark, keeps the letter, and has the `onerror` — all three at once |
| `test_the_brand_tile_letter_is_no_longer_invisible` | background and colour are not the same token |
| `test_the_login_page_brands_itself_before_first_paint` | server-rendered mark, `has-mark` ground, SVG still present |
| `test_every_branded_page_gets_the_resolved_urls` | all five branded pages call `get_branding()` |

**Why the asset test is a filesystem check and not an HTTP one.** `/assets/<app>/…` is
served off `sites/assets`, which is populated by `bench build`; a fresh CI site has run
`install-app` and nothing else. The thing that is true on **every** site, with no build and
no web server, is that the file is inside the app at the path the URL maps to. If that holds,
the URL holds wherever assets are built — and if it does not, no amount of building will help.

> **Test results and the fail-without-fix runs: see §9.** They were still pending when this
> section was written, because slice 013 was using `test_site`.

---

## 7 · The build step — the honest answer

| Environment | Does a new file under `public/images/` appear on its own? | Why |
|---|---|---|
| **dev and production** | **yes, automatically** | Every push builds a new container image. `deploy/Dockerfile:89-94` runs `bench build --production --app alvoraa_portal`, then line 107 runs `scripts/materialise_assets.sh` to turn the symlink into real files, because the nginx container has no `/apps` to follow a link into. The image ships the file. **`migrate` has no part in this** — assets are not a database thing |
| **the local bench** | **no** | `sites/assets/alvoraa_portal` in the `hrlocal-sites` volume is a baked copy, not a link. Nothing re-copies it |

Evidence it is a copy and not a link, taken before any change:

| Path | Bytes | Modified |
|---|---|---|
| `sites/assets/alvoraa_portal/js/portal_switch.js` (served) | 2,491 | 2026-09-10 |
| `apps/alvoraa_portal/.../public/js/portal_switch.js` (source) | 2,558 | 2026-09-05 |

Different sizes, different inodes: **the local bench has been serving a stale
`portal_switch.js` for nine days.** That is a second bug the build quietly fixes; §9 records
what actually changed.

**The alternative I rejected.** Frappe also serves binary files straight out of `<app>/www/`
through Python (`frappe/website/page_renderers/static_page.py`), with no build step at all.
That would have avoided this section entirely. I did not use it: that path goes through
gunicorn on every page load with no cache headers, while nginx serves `/assets/` with
`expires 30d; Cache-Control: public, immutable`. On the 3G phone budget, a cached
nginx-served mark is worth one build step that dev and production already perform by
themselves.

---

## 8 · The seven non-functional dimensions, against the code as written

| Dimension | Before → after | Verdict |
|---|---|---|
| **Performance** | Before: the navbar requested `/private/files/381140.jpg` on every page, was refused, and drew nothing — a wasted round trip per page view. After: 2.0 KB from nginx, `immutable`, cached 30 days, shared by every page and every tenant. **Zero new queries on any request path** — `get_branding()` reads `frappe.conf`, a dict already in memory, and the asset paths are module constants. The two extra dict keys are string references, not copies. `apply_site_branding()` does 5 single-value reads and at most 5 writes, and runs **once per site ever**, at install or in the patch — never on a request | **improves** |
| **Security** | Removes a case where a private file was linked from a public page. No new endpoint, no new whitelisted method, no new input. **No user-supplied value selects a file**: the paths are constants and `SLOTS` is a fixed tuple, so there is no path-traversal or doctype-injection surface. Writes go through `frappe.db.set_single_value` on two named Singles — no string-formatted SQL, no dynamic doctype. The patch does not use `ignore_permissions`, because it runs as a patch and touches no user-scoped document | **improves** |
| **Reliability** | Three layers deep: tenant logo → Alvoraa asset → the initial letter, with `onerror` making the last one real. `apply_site_branding()` is safe to run twice and has a test proving it. `brand.after_install()` catches everything and logs, because **a tenant that exists with the wrong logo beats a tenant that failed to install** — the same reasoning `tenant_api.py` already applies to the baseline step. `_verdict()` treats Frappe's own `attach_files:` placeholder as empty, which is a real value that field takes | **improves** |
| **Scalability** | Nothing here grows with headcount, months, tenants or transactions. One file, served by a web server, byte-identical for every customer. No background job needed because there is no work to queue | **neutral** |
| **Maintainability** | One module owns the paths and the rule. One artwork file plus one command is the entire swap. Before: the rule existed nowhere, the letter fallback was silently broken, and the login page had a second copy of the logo logic in JavaScript that fought the server. The `logos[0]` trap is written down at the place someone would otherwise walk into it | **improves** |
| **Data integrity** | Two Singles are written. **Cache invalidation is in this change, not a follow-up**: `frappe.clear_cache()` plus `frappe.website.utils.clear_website_cache()`, which is exactly what Frappe's own `WebsiteSettings.on_update` does — without it Guest keeps being served the old favicon until something else clears it. `get_single_value(..., cache=False)` on the read, because the patch runs after a migrate that may already have read these and a stale read is the difference between repairing a tenant and not. The patch commits explicitly | **neutral** (correct, with the care point handled) |
| **Compliance / privacy** | No personal data is touched. **Nothing personal is logged**: the log line carries the operation, the site name, the field names and the reason — never a file name, a person or a value. Exposure **narrows**: a private-file URL is removed from public HTML. **No visibility is widened** — nothing added to a list view, an export, a notification, a report or an API response. `get_tenant_config` (Guest-callable) is unchanged and still returns only what it already did | **improves** |

**Personas.** CXO, HR Manager and Employee all get the same thing: the right mark in the
rail, a real favicon, a branded sign-in page. The HR Manager and CXO additionally stop
seeing the Frappe framework logo in the desk navbar. **No persona gains or loses access to
anything** — no permission, role, row scope or endpoint was touched.

**Upgrade safety.** Everything is inside `alvoraa_portal`: an asset, one hook line, one
patch. No edit to `apps/frappe`, `apps/erpnext` or `apps/hrms`. `bench update` cannot undo
it. The one upstream behaviour relied on — `get_app_logo()`'s preference order — has a test
that fails if it changes.

**Accessibility.** The mark is decorative: the tenant's name is already text beside it, so
`alt=""` is correct and a screen reader reads the name once. **The old login page put the
tenant name in the `alt` as well, making it read twice; that is removed.** Colour is not the
only signal anywhere here. The tile uses `object-fit: contain`, so at 200 % zoom and 360 px
the mark scales with its box instead of cropping. Contrast of the letter fallback:
`--primary` on `--surface` passes AA in both themes, where before it was the same colour as
its own background.

**Internationalisation.** No new user-facing string. No date, currency or number format.

---

## 9 · What I ran, and what it said

> Filled in after the runs. Slice 013 held `test_site` when the code was written.

*(see the section below — appended after the runs completed)*

---

## 10 · What else moved while I worked

**Incoming commits: none.** `git fetch origin` left `origin/dev` at `baa9f68` throughout.
Local `dev` is `3f5ce3d`, two commits ahead and unpushed (slice 024's `99a17a4` and
`3f5ce3d`). I branched from local `dev`, so both were already under me. **No rebase was
needed and no conflict occurred** — there was nothing of anyone else's to merge, so there is
nothing to prove survived.

**Other sessions' uncommitted work in the main checkout**, none of it mine and none of it
staged by me: `.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`,
`docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`,
`hrms/.../alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and untracked
`INDIA_PAYROLL_STRATEGY.md`, `OBJECTIVES_AND_KPI_SRS.md`, `SETUP-GUIDE.md`, `docs/legal/`,
`docs/priorities/`, `docs/slices/013-mobile-app/`, `docs/slices/_template/`,
`docs/slices/009-ess-portal-redesign/01b-ux-design.md`.

**Overlaps, and how each was handled:**

| File | Who else | What I did |
|---|---|---|
| `hrms-employee.html` | slice 010 round 2 holds it — review lists, `prOpenManagerReview`, HR finalize, flag buttons, calibration note. Slice 013 states "NEVER hrms-employee.html" | **Split.** I changed two small regions — the `.sidebar-brand-logo` CSS rule and the brand tile — neither of which is in 010's list. Nothing moved, re-indented or renamed |
| `hooks.py` | slice 013 holds it (`doctype_js`, HR Settings `doc_events`, appends to `after_migrate`/`after_install`); slice 024 added a line at the top | **One line appended** at the end of `after_install`, with a comment, per the hot-file rule. On conflict, keep every entry from both sides |
| `patches.txt` | slice 013 claims "append after 014's line" | **One line appended at the end.** On conflict, keep both, in commit order |
| `docs/slices/009-…/` | another session has `00-assessment-and-plan.md` modified and `01b-ux-design.md` untracked | I added a **new** file, `09-brand-assets.md`. Their two files were not opened |
| `test_site` and the bench | slice 013 was running `run-tests --app alvoraa_portal` then `alvoraa_goals` in container `hrlocal-013` against the shared `test_site` | **I waited for it to finish.** No concurrent run, no `bench build` while theirs was in flight |

Board row added to `.claude/work-in-progress.md`.

---

## 11 · Known gaps and shortcuts, declared

1. **The artwork is a placeholder.** The biggest open item, and the reason nothing carrying
   type is displayed. §4 has the one command.
2. **A tenant that deliberately *cleared* a brand field will get ours back.** `_verdict()`
   cannot tell "nobody ever set this" from "somebody emptied it" — Frappe stores both as
   NULL. I judged that acceptable for fields whose only other outcome is a Frappe logo, and
   it is the one place the rule is not perfectly conservative. Fixing it properly would need
   a stored "the tenant chose blank" marker, which is a doctype for a hypothetical.
3. **`brand_logo_url` has no consumer.** It is exposed for the redesign and the wordmark
   question, so it is currently dead code with a comment saying so. If the redesign does not
   use it, delete it.
4. **`test_the_portal_never_renders_a_broken_image` reads `hrms-employee.html`'s markup.**
   When slice 009 replaces that template the test must be repointed. That is deliberate —
   it should make somebody stop and think — and `09-brand-assets.md` says so.
5. **The local bench's `sites/assets` will drift again.** Nothing keeps it in step with the
   app; it is a copy. dev and production are fine because the image is rebuilt per push. A
   proper fix is a bench-side symlink, which is a bench-configuration decision, not this
   slice's.
6. **With more time:** an SVG mark. The master is a raster, so the served files are rasters;
   an SVG would be smaller again, sharp at every size, and themeable with `currentColor`.
   Worth asking for a vector original along with the corrected wordmark — and if one
   arrives, `make_brand_assets.py` should learn to pass it through instead of rasterising it.
