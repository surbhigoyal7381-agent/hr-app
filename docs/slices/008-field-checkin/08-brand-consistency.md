# Brand consistency across Alvoraa — done, and what is left

**Written:** 12 Sep 2026 · **Asked for by:** Surbhi
**Status:** §1 and §2 are built. §3 is a backlog strategy, not started.

---

## 1. The problem that was found

A tenant's brand colour was being computed in **three different places, three
different ways**, so one customer saw three different shades of their own colour:

| Where | How | Problem |
|---|---|---|
| `design_system.html` | HSL, lightness clamped for contrast, before first paint | The good one |
| `alvoraa-login.html` | Its own `shadeHex()`, `deepen()`, `hexAlpha()`, fetched by API **after** the page drew | A different shade, **and** a visible flash of the default purple on the sign-in page — the first screen a customer's staff ever see |
| `www/field_checkin.py` | A third implementation, in Python | Added 12 Sep, removed the same day |

`accent_color` was worse: read in three files, **settable in none**. Every tenant
ever created had the same amber accent, whatever their brand.

## 2. What was done

### One implementation

`alvoraa_portal/templates/includes/brand_color.html` is now the only code that
turns a brand colour into a palette. It:

- runs **before first paint**, so nothing repaints
- **clamps lightness** so a pale brand cannot make white-on-colour unreadable —
  the rule that matters and the one not to soften
- sets `--primary`, `--primary-h`, `--primary-d`, `--primary-lt`, `--primary-rgb`,
  `--sidebar-bg`, `--hero-bg`
- now also sets `--accent`, `--accent-h`, `--accent-lt`
- sets the phone's `theme-color` from the computed token, so the status bar
  cannot disagree with the screen

Included by `design_system.html` (so every portal page gets it) and directly by
the field check-in app, which has its own type scale but the same colours.

The login page's own colour code and its three helper functions were deleted.

### Accent colour, end to end

| Step | File |
|---|---|
| Picker on the create form | `alvoraa-admin.html` → `f-accent` |
| Picker on the edit form | `alvoraa-admin.html` → `edit-accent` |
| `create_tenant(accent_color=...)` | `tenant_api.py` |
| `update_tenant(accent_color=...)` | `tenant_api.py` |
| Forwarded to the provisioning worker | `tenant_api.py` → `ACCENT_COLOR` |
| Written to the new site's config | `provision_tenant.sh` |
| Returned to the console so the form prefills | `tenant_api.py` |
| Read per site | `tenant_context.get_branding()` |
| Painted | `brand_color.html` |

Forwarding a new argument is safe across a mixed deploy: `_run_provision` takes
`**extra`, so a worker running an older image ignores it rather than failing.

### Where a tenant's colour now reaches

| Surface | Branded |
|---|---|
| Sign-in page | ✅ now server-side, no flash |
| Employee self-service portal | ✅ |
| Driver portal · Vendor portal · Goals portal | ✅ |
| Field check-in app on a phone | ✅ including the home-screen icon, app name and status bar |
| Alvoraa admin console | ❌ **on purpose** — it is our control plane, not a tenant's |
| **Frappe HR / ERPNext desk** (`/app`) | ❌ **not yet — see §3** |

## 3. Backlog: branding the Frappe HR and ERPNext desk

**Not started. Documented so it can be picked up deliberately.**

The desk at `/app` is the one place a customer's HR manager still sees Frappe's
own colours rather than their own. It matters because HR staff live in the desk,
while employees live in the portal — so today the two halves of the same product
look like two products.

### What Frappe already gives us, to check before building anything

| Mechanism | What it can do | To verify |
|---|---|---|
| **Website Settings → brand image / app logo** | Logo in the navbar | Already settable per site |
| **Navbar Settings** | Menu items, which we already touch in `portal_switch.js` | Confirmed present |
| **`app_include_css` / `app_include_js` hooks** | Inject a stylesheet into every desk page | We already use `app_include_js` |
| **Frappe UI CSS variables** | v15+ exposes desk theme variables | **Verify the exact names in the v16 source before designing** |
| **Workspace icons and colours** | Per-workspace accents | Partly config |

### The approach I would take

1. **Do not fork or patch Frappe's CSS.** Upgrade-safety is a standing rule, and
   a patched desk stylesheet is repaid at every version bump.
2. **Add `alvoraa_portal/public/css/desk_brand.css`** and register it in
   `app_include_css`. One file, additive, removable.
3. **Have it read the same site config values** via a tiny `app_include_js` that
   writes the tenant's colour into the desk's CSS variables — reusing the *same*
   maths as `brand_color.html`, not a fourth implementation. The cleanest way is
   to serve `brand_color.html`'s logic as a static asset both surfaces load.
4. **Scope it to the visual layer only** — navbar, primary buttons, active
   sidebar item, links. Do not repaint status colours (green/red/amber) for the
   same reason the field app does not: they mean something.
5. **Dark mode:** v16's desk has its own dark theme. The clamp must flip, exactly
   as `brand_color.html` already does.

### Risks to weigh first

- Frappe's desk CSS variable names are **not a public API** and can change
  between versions. Anything built here needs a check at every upgrade, and
  ideally a CI test that fails when a variable disappears.
- Contrast in the desk is harder than the portal: dense tables, small text, many
  states. The clamp may need to be stricter than 4.5:1.
- ERPNext modules we do not control (Accounts, Selling) will inherit whatever we
  set globally. That is desirable, but it must be tested, not assumed.

### Rough size

**M — around 2 to 3 days**, most of it verification rather than code: reading the
v16 desk source for the real variable names, then checking contrast across the
desk, dark mode, and a couple of ERPNext modules.

### Open question for the user

⚠ **Should the desk be branded at all?** There is an argument for leaving it
Alvoraa-and-Frappe-coloured: it is the administrative back office, and a visual
break between "the product your staff use" and "the system you administer" is
sometimes a feature. Worth deciding before the two to three days are spent.
