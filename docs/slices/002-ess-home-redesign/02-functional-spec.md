---
slice: 002-ess-home-redesign
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-09-09
status: draft
inputs: [01-product-brief.md]
scope: Phase one only — the visual system. Phases two to four get their own spec.
---

# Phase one: the design system

This spec covers **only** the visual system. The home page blocks and layout are
phases two to four and are deliberately excluded, because the brief requires
phase one to ship and be judged alone.

## What this turned out to be

It began as "make it look more professional". Measuring it changed the
justification:

**Every semantic colour in the portal today fails the accessibility standard.**

Contrast against the page background `#F8F6F3`, where body text needs 4.5:1:

| In use today | Ratio | Verdict |
|---|---|---|
| `#f59e0b` amber — used for warnings | **1.99** | Fails badly |
| `#16a373` green | **2.99** | Fails |
| `#43a047` green — 25 uses | **3.06** | Fails |
| `#3b82f6` blue | **3.41** | Fails |
| `#e53935` red — 35 uses | **3.92** | Fails |

A warning in amber at 1.99:1 is close to invisible to anyone with reduced
vision, on a poor screen, or in sunlight — which describes a store employee
checking their phone on the shop floor.

So this is not a cosmetic pass. It is a correctness fix that also happens to
deliver the look the brief asked for.

## Gap analysis

| Area | Verdict | Why |
|---|---|---|
| CSS custom properties | **Extend** | The page already defines tokens (`--bg`, `--text`, `--primary`, `--border`). The mechanism is right; there are too few tokens and most values bypass them |
| Dark theme | **Extend** | Already exists and works. Keep the mechanism, redefine only the token values |
| Colour values | **Build** | 120 distinct hex values must become a defined set |
| Type scale | **Build** | 29 sizes become 7 |
| Icons | **Build** | Emoji replaced with inline SVG. The sidebar already does this — copy that |
| Gradients | **Drop** | All 7 removed |
| Shadows | **Drop then build** | 43 distinct become 3 |
| Frappe desk styling | **Drop from scope** | The desk is Frappe's own UI. Not ours to restyle |
| A CSS framework | **Drop** | Tailwind or similar would be a rewrite. The tokens do the job |

## The inventory being replaced

Counted in `alvoraa_portal/www/hrms-employee.html` on 9 September 2026:

| Family | Distinct values | Most used |
|---|---|---|
| Reds | **21** | `#e53935` (35 uses) |
| Blues | **28** | `#3b82f6` (5 uses) |
| Greens | **18** | `#43a047` (25 uses) |
| Ambers / oranges | **14** | `#f59e0b` (10 uses) |
| Teals | **14** | `#6db5b8` (3 uses) |
| Purples | **11** | `#7c3aed` (3 uses) |
| Yellows | **4** | `#fef3c7` (6 uses) |
| Greys and whites | **10** | `#fff` (62 uses) |
| **Total** | **120 distinct, 405 uses** | |

Twenty-eight blues is the clearest evidence that no system exists. Blue is not
one of this product's brand colours and carries no meaning in it.

## The token system

Every value below is contrast-checked. Ratios are against the theme's own
background.

### Neutrals — warm, to match the existing cream ground

| Token | Light | Dark | Use |
|---|---|---|---|
| `--n-0` | `#FFFFFF` | `#211D28` | Card and sidebar surface |
| `--n-50` | `#FDFCFB` | `#1F1C19` | Raised surface |
| `--n-100` | `#F8F6F3` | `#1A1815` | Page background (unchanged) |
| `--n-200` | `#F0EDE8` | `#252220` | Hover fill, table stripe |
| `--n-300` | `#E4E0D9` | `#332F2B` | Hairline border |
| `--n-400` | `#C9C3B9` | `#464039` | Strong border, disabled |
| `--n-500` | `#A8A199` | `#6B655E` | Placeholder |
| `--n-600` | `#736D65` | `#A8A199` | Muted text — **4.74:1, passes** |
| `--n-900` | `#2D2622` | `#F0EDE8` | Body text — **13.79:1** (unchanged) |

The current `--border: #E8E5F2` is a cool purple-grey sitting on a warm cream
page. That mismatch is part of why the page reads as unconsidered. `--n-300` is
warm and belongs.

### Accent — one, and only one

| Token | Light | Dark | Ratio |
|---|---|---|---|
| `--accent` | `#5B4B8A` | `#A99AD4` | 6.91 / 6.97 — passes |
| `--accent-hover` | `#4A3D73` | `#BBAEE0` | — |
| `--accent-tint` | `#EDEAF4` | `#2A2438` | Background only |

The brand purple, kept as decided. Used for: the active sidebar item, primary
buttons, focus rings, and links. **Nothing else.**

### Semantic — three states, two shades each

| Token | Light | Ratio | Dark | Ratio | Replaces |
|---|---|---|---|---|---|
| `--good` | `#1B7F5A` | **4.60** | `#5DBF97` | 7.90 | 18 greens |
| `--good-bg` | `#E8F4EF` | — | `#12332A` | — | |
| `--warn` | `#9A6510` | **4.59** | `#E0A94A` | 8.39 | 14 ambers, 4 yellows |
| `--warn-bg` | `#FBF1E0` | — | `#33280F` | — | |
| `--bad` | `#B3261E` | **6.06** | `#F08A82` | 7.31 | 21 reds |
| `--bad-bg` | `#FBEAE8` | — | `#3A1C1A` | — | |

Every one passes 4.5:1 in both themes. Not one of the colours they replace does.

The `-bg` tokens are for fills behind text only, never for text.

### Type — seven steps

| Token | Size | Use | Replaces |
|---|---|---|---|
| `--fs-xs` | 11px | Labels, captions, table headers | 8, 9, 9.5, 10, 10.5, 11 |
| `--fs-sm` | 12px | Secondary text, metadata | 11.5, 12, 12.5 |
| `--fs-base` | 13px | Body, table cells, inputs | 13, 13.5, 14 |
| `--fs-md` | 15px | Card titles, emphasis | 14.5, 15, 16 |
| `--fs-lg` | 18px | Section headings | 17, 18, 19, 20 |
| `--fs-xl` | 24px | Page titles | 22, 24, 26, 28 |
| `--fs-2xl` | 32px | Single headline figures | 30, 32, 36, 38, 40, 52 |

Every number that lines up in a column gets
`font-variant-numeric: tabular-nums`. Most of this product is columns of
numbers, and proportional digits make them impossible to compare at a glance.

### Surfaces

| Token | Value | Use | Replaces |
|---|---|---|---|
| `--r-sm` | 6px | Inputs, buttons, pills | 2, 3, 4, 5, 6, 7 |
| `--r-md` | 10px | Cards, panels, dialogs | 8, 9, 10, 12 |
| `--r-full` | 999px | Avatars, badges | 20, 22, 50, 99, 100, 999 |
| `--sh-1` | `0 1px 2px rgba(0,0,0,.05)` | Sticky headers only | 43 shadows |
| `--sh-2` | `0 4px 12px rgba(0,0,0,.10)` | Dropdowns, popovers | |
| `--sh-3` | `0 12px 32px rgba(0,0,0,.16)` | Modal dialogs | |

**Cards get a border, not a shadow.** This is the single change that most
affects how calm the page reads. A shadow says "this floats above the page";
thirty cards cannot all float.

### Gradients

All seven `linear-gradient` declarations are removed. Flat colour throughout,
including buttons and the sidebar.

A gradient changes the colour of what sits under it, so the value is no longer
one value — it defeats the token system it would sit inside.

### Icons

The 135 emoji become inline SVG at one weight and one size, using
`currentColor`. The sidebar already does exactly this; that markup is the
pattern to copy.

## Permission matrix

Not applicable. This phase changes no data, no endpoint and no access rule.
Stated explicitly so the reviewer does not go looking.

## Data model

Not applicable. No doctype, field or migration.

## Acceptance criteria

Numbered, each with an oracle that can be checked without an opinion.

**AC-1 — Colours are a system**
Given the portal page,
When distinct hex values are counted,
Then there are **15 or fewer**, and every one is a token definition.

**AC-2 — Type is a scale**
Given the portal page,
When distinct `font-size` values are counted,
Then there are **7 or fewer**.

**AC-3 — Shadows are rare**
Given the portal page,
When distinct `box-shadow` values are counted,
Then there are **3 or fewer**.

**AC-4 — Radii are consistent**
Given the portal page,
When distinct `border-radius` values are counted,
Then there are **3 or fewer**.

**AC-5 — No gradients**
Given the portal page,
When `linear-gradient`, `radial-gradient` and `conic-gradient` are counted,
Then the count is **0**.

**AC-6 — No emoji as interface**
Given the portal page,
When characters in the emoji ranges are counted outside comments,
Then the count is **0**.

**AC-7 — Text is readable, light theme**
Given every foreground/background token pair used for text,
When contrast is computed,
Then every pair is **at least 4.5:1**.

**AC-8 — Text is readable, dark theme**
As AC-7, against the dark background. **At least 4.5:1**.

**AC-9 — Colour is never the only signal**
Given any element whose state is shown by colour,
When the page is rendered in greyscale,
Then the state is still distinguishable by text, icon or shape.

**AC-10 — Nothing lost**
Given the page before and after,
When panel count, nav item count and element ids are compared,
Then they are **identical**.

**AC-11 — Every screen still works**
Given each of the 13 panels,
When opened as an employee, a manager and an HR user,
Then each renders with no missing text, no invisible control and no
unstyled block.

**AC-12 — Both themes**
Given the light theme, the dark theme, and the system default with no
explicit choice,
When each panel is opened,
Then text is legible against its own background in all three.

AC-1 to AC-8 are machine-checkable and belong in CI. AC-9 to AC-12 need a
person.

## Non-functional numbers

| Dimension | Target | How measured |
|---|---|---|
| Page weight | No larger than today; SVG icons should make it smaller | Byte count of the rendered page |
| First paint | No slower than today | Same tenant, same browser, before and after |
| Requests | **Unchanged.** No web fonts, no icon font, no CSS framework | Network panel |
| Accessibility | WCAG 2.1 AA for contrast | AC-7, AC-8 |
| Browser support | Whatever works today | CSS custom properties are already in use |

**No new external resources.** Everything ships inside the page, as now.

## Migration and rollout

There is no data migration. The risk is entirely in the edit itself.

**Why this needs its own procedure.** All thirteen panels live in one file of
about 15,000 lines. On 9 September a script matching an ambiguous anchor deleted
2,760 lines of it — whole panels unrelated to the change. It was caught only
because the diff was read line by line.

Mandatory for every edit in this phase:

1. **Every anchor must match exactly once.** Assert the count before replacing.
2. **Count before and after**: panels, nav items, element ids, `<script>` blocks.
   Any difference stops the change.
3. **Parse the JavaScript** after each edit. A broken brace takes out every
   screen, not just the one being edited.
4. **One commit, cleanly revertable.** The brief's decision to ship to all
   tenants at once means redeploying the previous image is the only rollback.
5. **Order:** define tokens first, then replace values one family at a time —
   reds, then greens, then ambers, then blues, then neutrals. Each family is a
   reviewable step.

## Localisation and accessibility

- No new user-facing strings. Nothing to translate.
- Contrast: AC-7, AC-8.
- Colour independence: AC-9.
- Focus must stay visible — the accent focus ring is a token, not a per-control
  decision.
- Icons that convey meaning need an accessible label. Emoji carried one by
  accident; SVG does not, so `aria-label` or `<title>` is required wherever an
  icon is not purely decorative.
- `prefers-reduced-motion` must be respected by any transition kept.

## Audit trail

Not applicable. No data changes.

## ⚠ COMPLIANCE

**⚠ Accessibility — owner: Surbhi.** Today's palette fails WCAG 2.1 AA contrast
on every semantic colour. This is a live gap, not a new requirement, and worth
knowing for two reasons: enterprise customers ask about accessibility in
procurement, and it is a genuine barrier for employees with reduced vision. This
phase closes it. Whether we then *claim* AA conformance is a separate decision
needing a full audit — contrast is one of many criteria.

No personal data, no DPDP implication, no retention or consent impact.

## Traceability

| Brief requirement | Where it is met |
|---|---|
| "less colors" | Token system · AC-1 |
| "more professional and elegant" | Flat surfaces, one accent, real icons · AC-3, AC-4, AC-6 |
| "space utilization should be better" | Type scale and flat surfaces free the space. **The layout that spends it is phase four** |
| "remove any gradients" | Gradients section · AC-5 |
| Keep the purple | `--accent` `#5B4B8A` |
| Every tenant, all at once | Migration section, rollback procedure |

**One gap named honestly.** Phase one makes room but does not rearrange
anything, so "better space utilisation" is only half delivered here. The other
half is phase four. If that reads as under-delivering on the brief, the answer
is to schedule phase four immediately after — not to fold layout changes into
this one, which is what makes the rollback unsafe.

---

## Open questions

1. **Is 13px the right body size?** (owner: Surbhi) — Today's body text is
   mostly 13–14px. 13px is dense and suits a data product; 14px is easier for
   older eyes. This is a genuine trade-off between "more per screen" and
   "readable", and it should be a deliberate choice.
2. **Which icon set?** (owner: Surbhi) — Recommendation: draw the twenty or so
   needed by hand in the sidebar's existing style, rather than adding a library.
   The CSP allows no external stylesheets, and an icon font is a request we do
   not need.

## Assumptions

- `[ASSUMPTION]` The Frappe desk is out of scope. Only the portal pages change.
- `[ASSUMPTION]` `#F8F6F3` and `#2D2622` stay as background and text. Every
  other value is negotiable; these two anchor the palette.
- `[ASSUMPTION]` No change to any behaviour, endpoint or piece of data. If an
  edit requires one, it belongs in a different slice.
- `[ASSUMPTION]` The other portal pages — vendor, driver, goals, admin, login —
  get the same tokens, since they share the visual language. Their layouts are
  untouched.

## Handoff note

To the engineer: the token table is the specification. Do not improvise a value.
If a colour in the file maps to none of the tokens, that is a finding to raise,
not a judgement call to make — an improvised value is how the file reached 120.

Work one colour family at a time and commit each separately. Twenty-one reds
becoming two is a reviewable change; 120 values becoming twelve in one commit is
not reviewable by anyone.

The counting checks in AC-1 to AC-6 should be written **first**, before any
value is changed. They will fail, loudly, with today's numbers — and that
failing output is the baseline. Then the work is done when they pass.

Finally: the mapping is mechanical but not thoughtless. Some of the 120 will be
in a `<canvas>` call, a chart series, or an inline `style` on a demo block, and
a few will turn out to carry meaning that no token covers. Raise those rather
than forcing them into the nearest token.

## Ready check

| | |
|---|---|
| Brief approved | Yes — 9 September |
| Open questions blocking | **No.** Both are refinements; work can start on the token definitions |
| Data model settled | N/A — no data |
| ACs testable | Yes — 8 of 12 automatically |
| Rollback understood | Yes — redeploy previous image; one revertable commit |
| **Ready to build** | **Yes**, once the two open questions are answered or the recommendations accepted |
