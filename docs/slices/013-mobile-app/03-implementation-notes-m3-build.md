---
slice: 013-mobile-app
artifact: 03-implementation-notes-m3-build
ticket: ALV-133
author: hrms-fullstack-engineer
date: 2026-09-27
branch: slice/ux-mobile-m3-build (on origin/dev 98b8618, after the review rebase)
status: built, reviewed (Ship with fixes), fixes done - tested locally, not pushed
---

# 013 · Field app Material 3 redesign, as built (ALV-133)

**What this is.** The approved redesign (`01d-ux-redesign-m3.md`, prototype
`prototype-mobile-m3.html`, approved by Surbhi on 27 Sep 2026) built into the
app, plus the small server changes it needs. App version **0.3.0**.

**Bad news first.**

1. **Nothing here has run on a real phone.** Every screen was walked in headless
   Chrome at 360 px with the camera, location, secure storage and server faked
   (122 screenshots, all measured clean). Android's own WebView, its font-size
   setting and the real camera are not proven. The debug APK is built for that.
2. **Large text on a real phone is not wired.** The CSS scales with `--s`, and the
   screenshots prove 200 % holds. But I could not check whether Android's WebView
   follows the phone's font size; if it does not, a small native bridge must pass
   the scale in (01d §9.4, still open).
3. **At 200 % text the notice's first part does not fit above the Agree bar.**
   Security's rule is for 360 × 640 at normal text, and that holds on every notice
   screen. At 200 % the person scrolls, and the last part still scrolls clear.

## 1. Branch and base

- Branch `slice/ux-mobile-m3-build`, in my own worktree. First made from
  `slice/013-checkin-fixes` at 8c3305f, as asked, while `origin/dev` was 6411f73.
- **The merge story.** After my first build the check-in fixes were rebased and
  pushed to `dev` (8c3305f became **ee305b0**), with **98b8618** on top: old app
  builds' photo time read as UTC, and `_enforced_radius` (radius 0 when HR
  Settings has location tracking off). I moved my commits across with
  `git rebase --onto origin/dev 8c3305f slice/ux-mobile-m3-build`, so the old
  check-in commits were not replayed. It applied with no conflict.
- What else came into `dev` with it, read and not mine: 0ecf9fa and 4f81749
  (slice 052 brief and decisions, docs only) and 095410c (`.claude/context/
  change-process.md`: a new requirement goes to the product manager first).
  None touches the field app.
- I checked 98b8618's lines survived: `_enforced_radius`, `_radius_checked`,
  `_sends_bare_utc` and `FIRST_BUILD_WITH_OFFSET` are all in `field_checkin.py`,
  and its 16 tests pass on this branch.
- The design commit 2d7f0b9 was cherry-picked. It also carries 18 lines in
  `.claude/context/ux-learnings.md` - the designer's, not mine.

## 2. What I built, file by file

| File | Mechanism | What and why |
|---|---|---|
| `web/js/vendor/material-color-utilities.js` (+ licence) | vendor | Google's colour code 0.3.0, the five parts the app uses, joined into one plain script by pinned esbuild 0.28.2 (D-M3-3). 64.5 KB, **13.9 KB gzipped**. Pinned by SHA-256 in `check_app.mjs`. `scripts/vendor/build_mcu.mjs` rebuilds it. |
| `package.json`, lock | dev deps | `@material/material-color-utilities` 0.3.0 and `esbuild` 0.28.2, exact pins, devDependencies only - nothing new ships except the vendored file. |
| `web/css/app.css` | rewrite | The prototype's APP TOKENS and APP COMPONENTS on `:root`, dark roles under `prefers-color-scheme` (D-M3-1), fixed green/amber, the camera, sheet, dialog, snackbar. No inline styles (the CSP blocks them). |
| `web/index.html` | rewrite | Every screen in Material 3 markup. All element ids and `data-action` names the JS used are kept, except the "This is not me" and "Remove this phone" screens, which became a dialog and a bottom sheet. |
| `web/js/theme.js` | new | Palette from the brand colour; monochrome under chroma 8 (D-M3-5); follows the phone's theme and repaints when it changes; remembers the last colour so the loading screen is already the company's; greeting by the clock (D-M3-7). |
| `web/js/ui.js` | new | Icons (SVG built with DOM calls, no HTML strings), the notice's six parts with an icon per key, one look per problem screen, list rows, the welcome, dialog / sheet / snackbar with Escape and focus kept inside. |
| `web/js/strings.js` | new | Every new word in one object with `t(key, vars)`, ready for a translation. Older words stay beside their tested logic. |
| `web/js/signin.js`, `signin-core.js` | edit | Error card toned by code (`lookFor`: red for wrong details, amber lock for waits, calm info when it is not the person's fault), password box marked and emptied, show-password, "Company code · ppj · Change", joining-code button becomes the main one when password sign-in is off. **NETWORK_LOCKED uses security's words.** Brand colour from the sign-in answer. |
| `web/js/join.js` | edit | Brand colour from the code check; "This is not me" is a dialog; the notice with icons; welcome shared with sign-in. |
| `web/js/checkin.js` | rewrite of the DOM layer | Status card, rule inside it, one 96 px button in the brand colour for both In and Out (D-M3-2), skeleton while loading, camera screen restyled, three-step progress, result as a list with the true location and the photo thumbnail, problem template, Settings grouped list, Records, **Stop agreeing**, the remove sheet (no `window.confirm`). Every behaviour of ALV-128 and the check-in fixes is kept. |
| `web/js/checkin-screens.js` | edit | `whereLines` (01d §7.6 table), `homeRule` (uses the server's `check_in_rule`), `statusOf`, `whereShort`, distance format with whole km from 100 km. |
| `web/js/api.js`, `notice-cache.js` | edit | `withdrawAgreement`; `markWithdrawn` so the notice says "You stopped agreeing" after a withdrawal, also after a restart (M3-10). |
| `web/img/alvoraa-logo.png`, `alvoraa-mark.png` | copy | Surbhi's request: the logo above "Sign in", the mark in the bar on every screen before the company is known, "Powered by Alvoraa" in Settings → About. 10 KB. On a dark phone the logo sits on a pale tile so the purple still reads. |
| `android/.../res/mipmap-*`, `drawable*/splash.png`, `scripts/make_app_icons.py` | generate | Launcher icon (adaptive foreground on white, round and square older icons) and splash from the **1,600 px master** in `alvoraa_portal/brand/`, with the portal's own keying and cut. The monogram is 720 × 432 px, so even the 432 px foreground is a reduction: sharp. |
| `scripts/check_app.mjs` | edit | Pins the new vendored file; **fails any inline style in the page** (the CSP would drop it silently on the phone). |
| `android/app/build.gradle`, `web/js/app-version.js` | edit | 0.3.0, versionCode 30000. `MIN_APP_VERSION` not raised. |
| `alvoraa_portal/field_app_pwa.py` | edit | `brand_colour()`: always a plain `#rrggbb`, else the default. No query. |
| `alvoraa_portal/field_checkin.py` | edit | `field_status` adds `check_in_rule` ("radius" / "anywhere") and `brand_colour`. |
| `alvoraa_portal/field_app_join.py` | edit | The joined answer (code join and password sign-in) adds `brand_colour`; `withdraw_agreement` writes "The employee stopped agreeing to the notice in the app." on the phone's timeline. |
| `alvoraa_portal/field_app_notice.py` | edit | `ROW_KEYS`: a stable key per notice part (`record`, `not_record`, `why`, `who`, `how_long`, `rights`). **No word and no version changed.** |

## 3. The decisions, as built

| # | Decision | As built |
|---|---|---|
| D-M3-1 | Theme follows the phone | `color-scheme: light dark`, dark roles in CSS, `theme.js` repaints on change |
| D-M3-2 | One brand colour for In and Out | Done; the state is in the status card (colour, icon and words) |
| D-M3-3 | Vendor Google's colour code | Done, pinned, 13.9 KB gzipped |
| D-M3-4 | Agree reachable without scrolling | **Security's ruling applied:** the bar sits below the scroll area, never over it; the scroll area has bottom padding so the sixth part scrolls fully clear; at 360 × 640 the first part's heading and body are above the bar on all five notice screens (measured). Parts not collapsed; no forced scroll |
| D-M3-5 | Monochrome for colourless brands | Chroma under 8 → Material's monochrome scheme. PPJ's black gives black and greys, not pink |
| D-M3-6 | NETWORK_LOCKED words | **Security's words:** "Too many wrong sign-in attempts from this network. Try again in a few minutes, or turn off Wi-Fi and use your mobile data." Amber, lock icon |
| D-M3-7 | Greeting by time of day | Morning before 12, afternoon before 5 pm, evening after |

## 4. Server needs (01d §8)

| # | Result |
|---|---|
| E-1 | `brand_colour` in the sign-in/join answer and in `field_status`. Anything in site config that is not a hex colour gives the default. |
| E-2 | Already there from the check-in fixes (`location` on a saved punch). Used for the result. |
| E-3 | `check_in_rule` in `field_status`. A radius of 0 is "anywhere". The app falls back to the radius for an older server. |
| E-4 | Keys added in `rows_for()`, so the code join, the sign-in, `NOTICE_CHANGED` and `my_field_app_records` all carry them. The step-1 pin on the words and the version still passes unchanged. **Adding a key needed no new notice version.** |
| E-5 | HR already saw it (section state "Not agreed yet", "Changed by: The employee"). But the test site kept no Version row, so the timeline said nothing; one Info comment now says it in words. |

## 5. Deviations from the prototype (small, each on purpose)

- **Settings is not in the bar on the blocked / replaced problem screens.** Those
  screens appear before the app has today's status, so Settings would be half
  empty. The Remove button is on the screen itself. *Acceptable simplification.*
- **"Recorded today on this phone"** says "Your location and the time, and a photo
  if one was taken" - the status answer does not say which punch had a photo or
  where each was. *Acceptable simplification;* the design's wording needs a server
  field.
- **The result shows the person's own photo as the thumbnail** (the prototype drew
  a grey box). It is the photo just sent, from memory; nothing new is stored.
- **The sign-in screen shows the full logo instead of a bar**; the other
  pre-company screens show the mark in the bar (Surbhi's logo request).
- **The company's name is kept on the phone** (`alvoraa_company_name`) so a refusal
  on open (blocked, replaced) still names the company and shows its mark. Cleared
  with everything else when the phone is removed. A company name is not personal.

## 6. Acceptance (01d §14) and how each is met

| # | Criterion | Met by |
|---|---|---|
| 1 | Targets ≥ 48 px, text ≥ 12 px, nothing wider than 360 px at 200 % | Measured on 122 shots by `scripts/ux/shoot.mjs`: zero problems |
| 2 | Check In/Out the only 96 px button, bottom of Home | CSS `.btn.large`; test counts two uses (welcome, home) |
| 3 | Status card: three states, words + icon + colour; never "not yet" after Out | `statusOf` test; homeIdle/In/Out shots |
| 4 | Result location per §7.6; never "At" when not within | `whereLines` tests |
| 5 | Distance format | test |
| 6 | Notice words byte for byte; never pre-ticked; unticked Agree shows the error and moves focus | rows drawn from the server with textContent (test); no `checked` (test); `noticeUnticked` shot |
| 7 | Tick box and Agree visible at 360 × 640 | security's version, measured (see §3) |
| 8 | Stop agreeing calls `withdraw_agreement`, then the notice with its own words | API test, wiring test, `withdrawn` shots |
| 9 | Remove has one confirmation | no `window.confirm` anywhere (test) |
| 10 | Palette from `brand_colour`, monochrome under chroma 8, default before the company, fixed success/warning | tests |
| 11 | Light and dark, every text pair ≥ 4.5:1 | test: 15 pairs × 11 brand colours (black, grey, white, pale yellow, yellow, pale cyan, red, amber, Alvoraa, Sargam blue, the default green) × 2 themes |
| 12 | Every problem screen shows "Code for HR" | template; test |

## 7. Tests - what I ran and what it said

| What | Result |
|---|---|
| `npm test` (mobile/field-app) | **200 pass, 0 fail** (was 174; 25 new in `m3-redesign.test.js`, 1 in `check-app.test.js`) |
| `npm run check` | OK (app, dependencies, bundled files incl. the new pin); OK versionName 0.3.0, versionCode 30000; rises from 20100 |
| Server, own throwaway container `hrlocal-133` (the 013c site, database and Redis, my worktree mounted) | **320 tests, all OK**: check-in fixes 13, ALV-128 59, step 1 28, step 2 34, step 3 50, step 4 33, step 5 31, step 6 28, permissions 9, check-in location 9, check-in security 014 16, **ALV-133 10** |
| `scripts/check_app_integrity.py` | 654 checks, OK |
| `ruff` on changed Python | clean on every changed line (the files' existing F401 re-export notices are not mine) |
| Headless Chrome, `scripts/ux/shoot.mjs` | 122 shots (54 screens in light and dark, 200 % text for 9, 360 × 640 for the 5 notice screens), **0 problems** |
| Debug APK | built: 7.0 MB |

Two existing test pins changed with the design and say so in the test: the result
line (`whereLines`, was `whereLine`), the welcome rule (`whereShort`, was the long
sentence), the number of sign-out routes (4, was 3: Stop agreeing is new), the
NETWORK_LOCKED words, and the joined-answer and `field_status` key lists (+
`brand_colour`, `check_in_rule`).

## 8. The seven non-functional dimensions, against the code as written

| Dimension | Verdict | One line |
|---|---|---|
| Performance | neutral | +~40 KB gzipped of static assets loaded once from the APK, no new network call; the palette is worked out once per colour and remembered; server: no new query (`brand_colour` reads `frappe.conf` in memory). |
| Security | improves | Brand colour validated on both sides; icons built without HTML strings; a new check fails inline styles; the password is still never kept (show-password only flips the box type). |
| Reliability | neutral | Every flow and refusal path of ALV-128 and the check-in fixes is kept; theme fails soft to Alvoraa's colours; Stop agreeing handles no-internet inside the dialog and every other refusal through the existing gate. |
| Scalability | neutral | Nothing grows with headcount; two small fields on per-phone answers. |
| Maintainability | improves | One strings object, one problem template, one notice renderer, one look table; tests pin each new rule. |
| Data integrity | neutral | No schema change; withdrawal keeps every record; the phone's cached notice is marked, not deleted. |
| Compliance / privacy | improves | Withdrawal is now as easy as agreeing (DPDP), with a timeline line for HR; notice words and version unchanged; no new personal data shown or stored (the company name kept on the phone is not personal). |

## 9. Parallel work

- Files: the field app (`mobile/field-app/**`) and four server files
  (`field_app_join.py`, `field_checkin.py`, `field_app_notice.py`,
  `field_app_pwa.py`) plus their tests. `field_checkin.py` and
  `field_app_join.py` were also changed by the check-in fixes, which this branch
  sits on, so there is no overlap to resolve - this must land **after**
  `slice/013-checkin-fixes`.
- I did not touch the main checkout, the shared bench or its containers, or the
  work board (it lives in the main checkout).
- Containers: I made `hrlocal-133` (sleeping, stopped now) on the stopped 013c
  database, Redis and sites volume, and stopped all three when done.
  `hrlocal-013c` itself was not changed.

## 10. Review fixes (27 Sep 2026, verdict "Ship with fixes")

| # | Fix | Where |
|---|---|---|
| P2 | `check_in_rule` uses the enforced radius, so with tracking off it says "anywhere" beside `radius_m` 0, never "radius". The E-3 test now turns tracking on; a new test covers tracking off | `field_checkin._check_in_rule`, `test_field_app_m3_133` |
| P3 | The password box has `spellcheck="false" autocapitalize="none" autocorrect="off"`, so a keyboard cannot learn the password while "Show password" shows it | `index.html`, test |
| P3 | Older WebViews (minSdk 24): a plain declaration before every `inset` (Chrome 87), `color-mix()` (111) and `aspect-ratio` (88, now inside `@supports` with a padding square before it). A test holds the rule | `app.css`, test |
| P3 | `.gitattributes`: `mobile/field-app/web/js/vendor/*.js -text`, so a Windows checkout never breaks the hash pins. `git add --renormalize` showed no change to the committed blobs | `.gitattributes` |
| P3 | Security's rulings on D-M3-4 and D-M3-6 written into 01d §13 (and §7.1, §14) | `01d-ux-redesign-m3.md` |
| P3 | Two default colours, on purpose - see below | notes only |

**Two default colours, intended.** Before the app knows the company (sign-in,
joining code, problems before a company) it wears **Alvoraa's purple #5b4b8a**,
the portal's `--primary`: the screen is Alvoraa's, not a tenant's. Once the
company is known it wears **the tenant's own colour**, `brand_colour` from the
server. A tenant that never set one gets the server's default, **green
#1a7f5a** (`tenant_context.DEFAULTS`), the same colour its portal shows. So a
person may see purple at sign-in and green after it; that is the rule, not a
bug. The server default is not changed.

**Impact of the fixes.** Functional: one field (`check_in_rule`) now agrees with
`radius_m` when tracking is off; affects Home's rule line and Settings for every
persona using the app; HR desk and CXO views unchanged. Callers of
`_check_in_rule`: `field_status` only. NFR: security improves (keyboard
learning), reliability improves (older WebViews, Windows checkouts), everything
else neutral; one extra single-value read of HR Settings per `field_status`,
already cached by Frappe.

**Tests after the fixes:** `npm test` 202 pass, 0 fail; `npm run check` OK;
integrity 654 OK; ruff clean on changed lines; headless Chrome 122 shots, 0
problems; server suites in `hrlocal-133`: **194 tests OK** - ALV-133 11, check-in fixes 16, ALV-128 59, check-in location 9, check-in security 014 16, step 4 33, step 3 50;
debug APK 0.3.0 rebuilt.

**Still open for old WebViews (not fixed, cheap to leave):** flexbox `gap`
(Chrome 84) - an older WebView loses some spacing but nothing breaks; and
`:focus-visible` (86) - an older WebView shows the browser's own focus ring.

## 11. Known gaps

| Gap | Label |
|---|---|
| Not run on a real phone; WebView font size not verified | **temporary debt** - removed by the phone test with the debug APK |
| 200 % text: the notice's first part needs a scroll | intentional trade-off (security's rule is for normal text) |
| The status bar and navigation bar colours do not follow the theme (needs Capacitor's status-bar plugin) | temporary debt - a new plugin needs its own review (01d §9.5) |
| Hindi not built; older words not yet in `strings.js` | intentional (out of scope) |
| "Recorded today" line is generic (see §5) | acceptable simplification |
| `scripts/ux/shoot.mjs` needs Playwright, which is not an app dependency, so it is not in CI | acceptable simplification |
| `alvoraa_portal/brand.py` notes that the master's wordmark reads ALVORAA while "the chosen spelling is ALVORA". I used the logo as Surbhi asked; if the spelling note still stands, the sign-in logo needs new artwork | **ask Surbhi** |
