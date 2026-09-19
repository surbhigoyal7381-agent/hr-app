# Where the brand assets live — read this before building the new frame

**Added by slice 025, 19 September 2026.** This is a pointer, not a design change.
Nothing in `01b-ux-design.md`, `00-assessment-and-plan.md` or the appendices has been
edited.

## The one thing to know

The rail's brand mark is **already resolved for you** by the function
`appendix-a-frame.md` FR-18 says you will keep calling:

```python
from alvoraa_portal.tenant_context import get_branding
context.update(get_branding())
```

That now returns two extra keys:

| Key | What it is |
|---|---|
| `brand_mark_url` | the small square for the rail's `.mark` slot — **the tenant's own logo if it set one, otherwise the Alvoraa monogram** |
| `brand_logo_url` | the full lockup, for a wide slot such as a splash or a banner |

So the new frame gets the rule by doing what it already intended to do. **Do not build a
second resolution path, and do not hard-code an asset URL in the template.** The paths are
constants in `alvoraa_portal/alvoraa_portal/brand.py`; that module is the only place they
are written down.

## The files, and how they are served

| File in the app | Served at | What it is |
|---|---|---|
| `alvoraa_portal/public/images/alvoraa-mark.png` | `/assets/alvoraa_portal/images/alvoraa-mark.png` | the monogram, 128×128, transparent, 2.0 KB |
| `alvoraa_portal/public/images/alvoraa-logo.png` | `…/alvoraa-logo.png` | the full lockup, 320×187, transparent, 8.0 KB |
| `alvoraa_portal/public/images/alvoraa-favicon.png` | `…/alvoraa-favicon.png` | 32×32, on white, 1.1 KB |

nginx serves `/assets/` off disk with `expires 30d; Cache-Control: public, immutable`, so
the mark is fetched once and then free. The master artwork is at
`alvoraa_portal/brand/alvoraa-logo-master.jpg` and is **not** served; the three files above
are regenerated from it by `python scripts/make_brand_assets.py`.

## Two things the redesign must not lose

**1. The rail mark must not be able to draw a broken-image icon.** That was the reported
bug. The pattern in `hrms-employee.html` keeps the tenant's initial letter in the tile
*underneath* the image and gives the image an `onerror` that removes itself:

```html
<div class="sidebar-brand-logo">{{ tenant_name[0] | upper }}{% if brand_mark_url %}<img
  src="{{ brand_mark_url }}" alt="" onerror="this.remove()">{% endif %}</div>
```

The prototype's rail renders `<div class="mark">${TENANT.mark}</div>`
(`prototype-v2.html:828`). **Carry the fallback and the `onerror` across when you turn that
into a Jinja template**, or the new frame reintroduces the fault this slice fixed. There is
a test on it — `tests/test_brand_logo_025.py::test_the_portal_never_renders_a_broken_image`
— and it reads the `hrms-employee.html` markup, so **it will need repointing at the new
template when the frame is replaced.** That is deliberate: it should make somebody stop and
think.

**2. The tile's text colour must not equal its background token.** The old rule set
`background:var(--surface)` and `color:var(--surface)` — the same custom property — so the
initial was invisible in both themes for as long as the tile existed. It is `var(--primary)`
now. `appendix-a-frame.md` notes that the prototype's `--tenant` tokens are not in
`design_system.html`; when you add them, **do not reuse one token for both the ground and
the text on it.** There is a test on that too:
`test_the_brand_tile_letter_is_no_longer_invisible`.

## One open item that affects the visual design

The wordmark spelling is **not settled**. The user chose "ALVORA" (one A); the artwork on
disk is a placeholder reading "ALVORAA" (two). Because of that, **nothing carrying type is
displayed anywhere yet** — every visible slot uses the monogram, which has no lettering and
is correct either way. If the redesign wants the wordmark in the rail's sub-line, use the
text string, not the image, until the real artwork lands. See
`docs/slices/025-brand-logo/03-implementation-notes.md`.

Accessibility note for the new frame: the mark is decorative because the tenant's name is
already text beside it, so `alt=""` is correct. Putting the name in the `alt` as well makes
a screen reader read it twice — the old login page did exactly that, and slice 025 removed
it.
