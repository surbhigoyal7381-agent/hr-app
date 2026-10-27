---
slice: 062-ess-phone-install
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-10-27
status: built locally, not pushed
inputs: [02-functional-spec.md, 00-decisions.md, alvoraa_portal/alvoraa_portal/field_app_pwa.py]
---

# Slice 062 — the portal installs on a phone's home screen

Built on branch `slice/062-ess-phone-install` in `.claude/worktrees/062-ess-phone-install`,
cut from `origin/dev` at `5f423750`. **Nothing pushed, nothing committed to `dev`, no
deploy command run, no live tenant touched.**

## The strategy, in short

Three small things, in two files.

| Rung of the cost ladder | What I did | Why not the cheaper rung |
|---|---|---|
| **Already there** | Reused `field_app_pwa.py` whole — `_brand()`, `brand_colour()`, `_darker()`, the werkzeug-Response trick for the worker header, the endpoint-not-a-file pattern | Nothing on this rung serves the portal. The check-in app's three endpoints say `/checkin` in four places |
| **Configuration** | — | A manifest cannot be configured into existence |
| **Customisation** | — | Frappe has no PWA setting |
| **New code** | Three new functions in the module that already holds the other three, plus six lines of tags and six lines of script in the page | This is the rung |
| **New DocType / new app** | — | Nothing is stored |

**Why three new endpoints rather than parameters on the existing three.** Every value
differs between the two apps — the name, the start URL, the scope and the
`Service-Worker-Allowed` header. Sharing would mean a branch inside each of the three
functions, which is more code than writing three, and it would put the check-in app —
installed on drivers' phones today — one bad branch away from breaking.

**Why the registration is in the page, not in `portal.js`.** `portal.js` has 61 incoming
commits we do not have and four other sessions in it. The registration needs nothing from
it. Six lines of inline script is a fair price for not queueing behind four merges.

## What I built, file by file

### `alvoraa_portal/alvoraa_portal/field_app_pwa.py` (+ ~120 lines, appended)

| Added | Mechanism | One line on why |
|---|---|---|
| `PORTAL_APP_NAME = "Alvora"`, `_PORTAL_SCOPE = "/hrms-employee"` | new code | Decisions 4, 5 and 3 as constants, each with the decision written beside it |
| `_MARK_SOURCE` | new code | Path to `brand/alvoraa-logo-master.jpg`, built from `__file__` |
| `_mark_mask(box)` | new code | Turns the master artwork into a white silhouette of the monogram, sized to fit |
| `portal_app_icon(size)` | new code | The icon: the mark on the tenant's `_darker()` ground |
| `portal_manifest()` | new code | `name` "Alvora", `start_url`/`scope` `/hrms-employee`, `display` standalone, three icons |
| `portal_service_worker()` | new code | The do-nothing worker, with `Service-Worker-Allowed: /hrms-employee` |

**Nothing existing was changed.** `app_icon()`, `manifest()` and `service_worker()` are
byte-for-byte what they were, so the check-in app is untouched. Two tests prove that.

### `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` (+ ~30 lines, of which 18 are comment)

- In `{% block head_include %}`: `<link rel="manifest">`, `<link rel="apple-touch-icon">`,
  `apple-mobile-web-app-capable`, `mobile-web-app-capable`,
  `apple-mobile-web-app-title` = `Alvora`.
- At the end of `{% block page_content %}`: a six-line registration, after the
  `portal.js` tag.

### `alvoraa_portal/alvoraa_portal/tests/test_portal_pwa_062.py` (new, 22 tests)

## Three traps found and paid for

**0. The manifest was being served wrapped, and would have installed nothing.** This is
the one that would have shipped as "we built it and it doesn't work". Setting
`frappe.local.response.type = "json"` and returning a dict — the obvious way, and the way
the check-in manifest does it — makes Frappe send

```json
{"type": "json", "message": {"name": "Alvora", "start_url": "/hrms-employee", ...}}
```

A browser reading a manifest unwraps nothing. Chrome would have seen an object with no
`name`, no `start_url` and no `icons`, and declined to offer the install — with no error,
no warning, nothing in the console. **I only found it because I fetched the endpoint over
HTTP instead of trusting the unit test**, which was reading the dict the function builds
internally. The manifest is now returned as a werkzeug `Response` with
`application/manifest+json`, the same shape the worker already uses, and the test parses
the response body the way a browser does.

**Worth saying out loud: the check-in app's manifest has the same wrapper.** I did not
touch it — leaving check-in exactly as it is was an instruction, and it is a separate
question whether its install prompt works today. **It is worth five minutes to check.**



**1. `frappe.get_app_source_path()` scrubs its arguments.** It turned
`alvoraa-logo-master.jpg` into `alvoraa_logo_master.jpg` and every icon call raised
`FileNotFoundError`. The path is now built from `__file__`, the same way
`tests/test_brand_logo_025.py` does, with the reason written beside it. **A test caught
this, not a human reading the code** — which is exactly what the tests are for.

**2. `apple-mobile-web-app-status-bar-style` is deliberately absent.** The check-in page
sets it to `black-translucent`, and copying that line across looked obviously right.
It is not: that page is built for it, with `env(safe-area-inset-*)` throughout. The
portal is not — `frame.css:30` pins the navbar at `top:0` with no inset — so the iPhone
clock would have sat on top of the header. Left out, which gives an opaque bar. There is
a test and a comment so nobody "completes the set" later.

## The icon: what I judged, and what I can show

Decision 4 left the artwork source to me: the 1600 × 1600 master, or the existing 128 px
`alvoraa-mark.png`. **I rendered both and compared.** At 512 the 128 px source is visibly
soft — a 2.2× upscale. The master is crisp at every size. The master wins; it costs one
file read, cached per worker process.

I also corrected my own first attempt at the maskable safe zone. Android promises not to
crop inside a **circle** of 80 % of the width, and the mark is about 2.5 times wider than
it is tall. Fitting it to a 56 % *square* — the largest square inside that circle — left
it a third of the size it could safely be. Fitting by the mark's own **diagonal** uses the
whole safe circle. The difference is plainly visible.

**Rendered and inspected at 192 and 512, on three tenant colours** — the default purple,
a deep green, and a pale yellow (`#FFF9C4`) to prove `_darker()` still earns its keep: it
darkened the yellow to an olive that white reads on. A test asserts the WCAG AA contrast
rather than trusting the eye.

**What I have not done, and it is the spec's own ask:** a screenshot of the 192 icon at
actual home-screen size on a real handset. That needs a phone, and it is five minutes.
The analyst asked for it before ship, and I agree.

## Acceptance criteria

The decisions file overrides the spec where they disagree, so AC-11, AC-13 and AC-15 are
read against decisions 4 and 5, not against the spec's text.

| AC | Status | How |
|---|---|---|
| 1 manifest link in the page | met | `test_the_page_links_the_portal_manifest` |
| 2 manifest 200, JSON, start_url/scope/display/icons | met | `test_the_manifest_is_served_unwrapped_as_a_browser_reads_it`, `..._starts_and_scopes_at_the_portal`, `..._offers_the_three_icons_chrome_documents`. Confirmed over HTTP: 200, `application/manifest+json` |
| 3 name from tenant_name | **superseded by decision 5** | Name is the constant "Alvora". `test_the_name_is_always_alvora_never_the_tenants` asserts a DTC tenant name does **not** appear |
| 4 worker activated, scope `/hrms-employee` | **needs a phone/DevTools** | Server side proven: header and registration scope both `/hrms-employee` |
| 5 `Service-Worker-Allowed: /hrms-employee`, no-store | met | `test_the_worker_is_scoped_to_the_portal_and_not_the_whole_site`, `..._served_as_javascript_and_never_cached` |
| 6 no caches anywhere | met | `test_the_worker_caches_nothing` greps the body for `caches`, `cache.put`, `respondWith`, `CacheStorage` |
| 7 `/checkin`, `/alvoraa-login`, `/app` not controlled | met | `test_the_portal_scope_does_not_cover_the_other_doors` |
| 8 Chrome offers "Install", no address bar | **needs an Android handset** | Everything Chrome requires is in place: manifest, 192 + 512 icons, `display: standalone`, same-origin start URL in scope, a worker with a fetch handler, HTTPS |
| 9 expired session leaves scope and shows a bar | **expected, not a defect** | `/alvoraa-login` is outside `/hrms-employee`, so this will happen. Written down here so nobody files it |
| 10 no iOS banner | met by Apple, nothing to build | — |
| 11 iOS label + icon | met, **label is "Alvora"** per decision 5 | `test_the_home_screen_name_is_alvora_not_the_tenant` |
| 12 icon is the Alvora mark, not the lockup, not the tick | met | `_mark_mask` cuts at the blank row between monogram and wordmark; rendered and inspected |
| 13 tenant with own logo shows that logo | **deleted by decision 4** | Reversed into `test_the_icon_ignores_the_tenants_own_logo`, which asserts the bytes are identical with and without a tenant logo |
| 14 maskable tile filled, mark in the middle 80 % | met | `test_a_maskable_icon_is_filled_to_every_edge` (RGB, one corner colour), `test_the_mark_stays_inside_the_circle_android_will_not_crop` (pixel scan) |
| 15 unreadable tenant logo falls back, never 500 | **deleted by decision 4** — no tenant logo is ever read | The surviving risk is a bad *colour*, so `test_the_icon_survives_a_tenant_colour_that_is_not_a_colour` covers that instead |
| 16 drawn from the 1600 × 1600 master | met | `test_the_mark_comes_from_the_master_artwork` |
| 17 check-in unchanged | met | `test_the_checkin_manifest_still_points_at_checkin`, `test_the_checkin_endpoints_keep_their_old_addresses` |
| 18 no collision with Frappe HR's own manifest | met | Nothing here links or registers `/assets/hrms/frontend/`; our scope is `/hrms-employee`, theirs `/hrms` |

**Three ACs cannot be closed from a keyboard** — 4, 8 and the visual half of 11 need a real
handset. Everything a server can prove is proven.

## The seven non-functional dimensions, against the code I wrote

| Dimension | Verdict | One line |
|---|---|---|
| **Performance** | neutral | Zero new queries; `frappe.conf` is already in memory. Page payload +~700 bytes of tags and script, most of it comment. The icon is drawn once per size per worker process (`lru_cache`) — about 60 ms cold, free after |
| **Security** | neutral | Three `allow_guest` GET endpoints that read no document and take no input but an integer size, clamped to 48–1024. The worker caches **nothing**, so no signed-in page or CSRF token can ever enter a store. The scope is `/hrms-employee`, so this worker can never touch the login page or the desk |
| **Reliability** | improves slightly | A failed registration is swallowed and the portal is unaffected — installing is a bonus, not a dependency. A malformed tenant colour gives the default icon rather than a 500 |
| **Scalability** | neutral | Nothing grows with headcount. The icon is the only CPU cost and it is cached per process |
| **Maintainability** | neutral | +~120 lines in a module that already held the same three ideas, and the three decisions that will look like inconsistencies in six months are each written beside the code and pinned by a named test |
| **Data integrity** | neutral | Nothing is written or cached |
| **Compliance / privacy** | neutral | No personal data is read, shown, logged or stored. The manifest and the icon carry a tenant's colour and nothing else — no tenant name, no employee data. No new log line |

Three personas: **CXO, HR Manager and Employee all see the same thing** — the portal
becomes installable. No permission, no data and no screen changes for any of them.

## Tests and what they really said

**The slice's own module, final run after every change:**

```
bench --site test_site run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_portal_pwa_062
  Ran 11 tests  OK      (batch 1)
  Ran 12 tests  OK      (batch 2)        -> 23 tests, all passing, exit 0
```

`bench run-tests` prints **two** batch summaries. Both are reported, because reading only
the tail hides a whole batch - usually the bigger one.

**Every other test module that reads the portal page or this PWA module** was run too -
the list is every module importing `tests/portal_source.py`, plus the two check-in app
modules. All of them pass:

| Module | Result |
|---|---|
| `test_brand_logo_025` | Ran 15, OK |
| `test_browser_call_args_045` | Ran 6, OK |
| `test_data_review_page_012` | Ran 5, OK |
| `test_ess_parts_034` | Ran 8, OK |
| `test_field_app_m3_133` (check-in PWA) | Ran 11, OK |
| `test_field_app_step1_013` (check-in app) | Ran 15 + 13, one error - see below |
| `test_portal_layout` | Ran 3, OK |
| `test_portal_split_034` | Ran 12, OK |
| `test_panel_source_042` | Ran 7, OK |
| `test_preview_page_034` | Ran 16, OK (4 skipped) |
| `test_portal_call_paths` | Ran 7, OK |
| `test_portal_csrf` | Ran 4, OK |
| `test_nav_consolidation_060` | Ran 15, OK |

**Three modules errored, and none of them is this change.** `test_home_holidays_035`,
`test_leave_ledger_035` and one leaver test in `test_field_app_step1_013` failed in
`setUpClass` while creating fixtures. I re-ran one and read the exception rather than
guessing: **`TimestampMismatchError: holiday.worker035@example.com (User) has been
modified after you have opened it`** - another process changing the same row mid-test.
At that moment three test runs were sharing `test_site`: mine, my own orphaned full-suite
run, and another session's. **This code writes no document at all** - it reads
`frappe.conf`, which is already in memory, and one JPEG off disk - so it cannot produce
a timestamp mismatch on a User row. Reported as environment, not as a code failure.

**The full `alvoraa_portal` suite was NOT completed, and here is the honest reason.** It
has a second batch of 1,041 tests, several of which take 30 seconds each, so it runs for
hours. I started it, and partway through found that **another session was running tests
on the same site at the same time** - `test_module_access`, repeatedly, clearly
mid-iteration. Two runs against one `test_site` make both results untrustworthy, and the
rule is one run at a time. I tried to stop my own run and was blocked from killing the
process, so it had to expire on its own. I restored the main checkout immediately so that
the other session was never reading my files, and ran the targeted set above once the
slot was free.

Three real faults were found on the way, all three by actually running things rather than
by reading the code: the wrapped manifest, the scrubbed artwork path, and an assertion of
mine that matched its own explanatory comment.

Other checks run:

```
python scripts/check_app_integrity.py        837 checks, OK - all consistent
jinja2.Environment().parse(hrms-employee.html)   parses, no syntax error
curl of all three endpoints over HTTP        200 / application/manifest+json,
                                             200 / application/javascript with
                                             Service-Worker-Allowed: /hrms-employee,
                                             200 / image/png 192x192 RGB
```

## Subtract pass — what I deleted

- **`_SAFE_DIAMETER = 0.80`** — a constant with one caller is just the caller. Inlined,
  with the reasoning moved to the use site.
- **`"orientation": "portrait"`** in the manifest — copied from the check-in app without
  thinking. That app is a camera page held upright; the portal is responsive and people
  use it on tablets. Pinning the orientation of an installed app is a behaviour change
  this slice was not asked for.
- **A second manifest/worker/icon module** — not created; the three new functions sit in
  the module that already holds the matching three.
- **A shared helper behind both apps' manifests** — not written; it would have been a
  branch in three places and a risk to the live check-in app.
- **A `theme-color` meta tag on the page** — the manifest already carries `theme_color`,
  which is what an installed app uses.
- **Any edit to `portal.js`** — deliberately avoided.
- **Any caching, kill switch, flag or DocType** — none built. The caching precondition is
  one comment in the worker's source, as decision 2 asks: before anyone adds caching, the
  build version must be inside the worker body and a kill switch must exist.

## What else moved while I worked

`git fetch origin dev` brought in **192 commits** that local `dev` did not have. **None of
them touch any file in this slice** — `field_app_pwa.py`, `www/hrms-employee.html`,
`www/field-checkin.html`, `tenant_context.py` and `www/hrms_employee.py` are all identical
between `dev` and `origin/dev`. No conflict, nothing to resolve, nothing of anyone else's
at risk.

`slice/074-signout` is unmerged and edits `frame.html` and `frame.css`. **I touched
neither**, so the two sit together with no conflict at all.

The main checkout holds other sessions' uncommitted work in `module_access.py`,
`tenant_api.py`, `alvoraa-admin.html` and others. **I left every one of them alone.** The
bench bind-mounts the main checkout, so to run the tests I copied my three files in,
ran, and restored the two tracked ones from a backup taken first. All three were
unmodified by anybody and identical to `origin/dev` before I started — verified with
`git status --porcelain` and `git diff origin/dev` — so nothing of anyone else's was ever
in the way.

## Known gaps

| | What | Label |
|---|---|---|
| 1 | AC-4, AC-8 and the visual half of AC-11 need a real Android handset and an iPhone. Everything a server can prove is proven | **acceptable simplification** — a phone test is the only way to close these |
| 2 | No screenshot of the 192 icon at actual home-screen size, which the spec asks for before ship | **temporary debt** — five minutes with a phone removes it |
| 3 | An installed app that hits an expired session lands on `/alvoraa-login`, outside scope, so the window grows a small in-app bar (AC-9) | **intentional trade-off** — the alternative is putting the login page in the worker's scope, which is worse |
| 4 | The sign-out on a phone is two taps behind an unlabelled initial circle. Decision 7 says this slice ships anyway, and `slice/074-signout` has the labelled button, tested and unmerged | **not mine to fix here**, but worth saying plainly: DTC has 441 staff logins on shared handsets, and installing makes the portal look more private than it is. I would land `slice/074-signout` in the same release |
