---
slice: ALV-149-brand-spelling (plus ALV-152, ALV-153)
status: BUILT LOCALLY. Not pushed, not merged into dev, no server touched.
date: 2026-09-27
owner: hrms-fullstack-engineer
approved: Surbhi, 27 Sep 2026, "go ahead as recommended" (answers 1-8 in section 9)
---

# ALV-149 · Implementation notes

**Bad news first.**

1. **The dry-run has NOT been run on dev or production.** It is a server command,
   so it waits for Surbhi's word. It ran read-only on the two local sites only
   (section 5).
2. **One change from the plan: the website banner keeps the MARK, not the new
   lockup.** Frappe caps a navbar banner image at 22 px high
   (`public/scss/website/navbar.scss`), so the ALVORA wordmark would be about 6 px
   tall there. The desk splash (200 px wide) and the phone sign-in do show the full
   lockup. One line in `brand.py` changes it if Surbhi wants the lockup anyway.
3. **Two failures in the full suite, neither caused by this slice** (section 7a).
4. **The patch does not leave a Version row.** The strategy said it would. I followed
   `brand.py`'s established pattern instead (`frappe.db.set_single_value` plus a cache
   clear), because saving System Settings through the ORM runs every one of its
   validations during a migrate. What changed is printed by the patch and written to
   the `alvoraa.brand` log with old and new values. Say if you want the Version row;
   it is a small change.

## 1 · What came in while I worked

- Start of the build: **nothing new on `origin/dev`** since a729d61 (slice 051,
  already named in the strategy). The ALV-133 phone redesign (1ee46e0) was already in
  my base.
- Before the artwork swap: **one commit came in, 3bb22ac** "053 brief: translate the
  frontline first..." - one new file,
  `docs/slices/053-languages-existing-portal/01-product-brief.md`. No overlap. Rebased
  cleanly; every commit hash here is after that rebase.
- Docker restarted during my first full run, which was lost; section 7a is the second
  run, on the same site.

## 2 · What was built, commit by commit

| Commit | What | Mechanism |
|---|---|---|
| 5c9859e | `scripts/check_brand_spelling.py`, report mode | new repository check; parses Python with `ast`; allow-list computed from the doctype JSON and `modules.txt` |
| e24aca5 | `app_title` "Alvora HRMS" (`alvoraa_portal/hooks.py`), "Alvora Goals" (`alvoraa_goals/hooks.py`) | configure: one line each |
| e5222bc | Screen, email and message text in 17 files, 3 tests follow | direct text edits, only the visible word; identifiers, routes and doctype names on the same lines untouched |
| d7f04dc | Phone app 0.3.1: brand strings, `strings.xml`, `capacitor.config.json` appName, sign-in shows the mark; 2 new tests | direct edits; `co.alvoraa.app`, the `X-Alvoraa-App-Version` header, JS names and image file names unchanged |
| 49dd1b2 | `alvoraa_portal/translations/en.csv`, 41 rows | Frappe's own English translation layer - no doctype renamed |
| 0a25b7c | `brand_text.py`, patch `alvora_brand_text`, `after_install`, `scripts/brand_text_dry_run.sh`, `.gitattributes` (the script stays LF) | exact-match patch; read-only SQL dry-run |
| 4756d22 | ALV-152: Action row, patch `navbar_portal_switch_as_action`, `portal_switch.js` deleted, tests replaced | data Frappe's menu runs; no desk JS |
| c15e925 | ALV-153: two selectors in `frame.css`; `tests/test_brand_spelling_149.py` | CSS on the portal page only |
| a019440 | The guard in CI (lint job), `brand_text.py` allowed to hold the old spellings | one CI step, `--self-test` first |
| ce51952 | One enrol-page test still asserted the old sentence (found by the full run) | test follows the text |
| 7a4ff3c | The real ALVORA artwork (section 6) | regenerated from the master; patch `alvora_splash_lockup` |
| (this commit) | These notes, and `scripts/browser_check_brand_menus.js` | hands-on browser check, not CI |

Files outside `alvoraa_portal`: `alvoraa_goals/hooks.py` (one line), `mobile/field-app`
(brand strings only, per the coordinator's note about ALV-151), `scripts/`,
`.github/workflows/ci.yml` (one step appended), `.gitattributes` (one line). **The
`hrms` fork, erpnext and crm are untouched.**

## 3 · Acceptance criteria (brief section 5)

| # | Criterion | How it is met | Proof |
|---|---|---|---|
| 1 | Login, portal, ESS, tab titles and phone say "Alvora" | text edits + `tenant_context` default + `app_name` patch + `en.csv` | guard: 0 visible hits in the repository; tests below |
| 2 | Email From name and text say Alvora; address unchanged | new-phone email subject/body edited; Email Account names respelled only when exact | `test_alv149_email_account_from_name_is_respelled_only_when_exact`, `test_field_app_password_signin_128` (subject) |
| 3 | No screen shows the ALVORAA lockup | sign-in `src` now the mark; portal already used the mark | `ALV-149: no screen shows the ALVORAA lockup` (node test); APK checked with `unzip` |
| 4 | Launcher shows "Alvora Attendance"; installs over 0.3.0 | `strings.xml`, appName; same app id, versionCode 30100 > 30000 | `aapt2 dump badging`: label `Alvora Attendance`, `co.alvoraa.app.debug`, 0.3.1-debug |
| 5 | Notice version unchanged | `field_app_notice.py` not touched | `git diff` |
| 6 | A value a tenant typed survives the patch | exact-match rule | `test_alv149_a_value_the_tenant_typed_survives` |
| 7 | The guard fails on "Alvoraa" in a template, passes on domains and ids | `--self-test` (11 cases) + a hand-made break in `enrol.html` | printed FAIL with file and line; restored |
| 8 | No package, doctype, URL or app id changed; existing tests pass | — | section 7 |

ALV-152: `test_alv152_*` (5 tests). ALV-153: `test_alv153_*` (2 tests).

## 4 · The seven non-functional dimensions, against the code written

| Dimension | Before → after | Verdict |
|---|---|---|
| Performance | Desk loaded `portal_switch.js` and polled the DOM every 2 s → no desk script. Boot translations grow by 41 short rows. No new query on any page | **improves** |
| Security | No endpoint, permission or `ignore_permissions` change. The Action string is the same trust level as Frappe's own "Reload" row. The CSS hides links; the desk stays guarded by module profiles on the server | **neutral** |
| Reliability | Patch catches per-setting failures into the Error Log and never fails a migrate; the navbar patch only upgrades an existing row | **neutral** |
| Scalability | Nothing grows with headcount; an Email Account rename is a one-off per tenant | **neutral** |
| Maintainability | One rule enforced by CI; misleading tests replaced by behaviour tests; a dead script removed | **improves** |
| Data integrity | Only exact old defaults change; dry-run and patch share one list, pinned by `test_alv149_dry_run_script_uses_the_same_rules`. No Version row (bad news 4) | **neutral** |
| Compliance / privacy | No personal data read, logged or shown. Logs hold setting names and product-name values only | **neutral** |

**Query count:** `brand_text.plan()` makes about 9 small reads per site, once, at
migrate or install. No request-time cost.

## 5 · The dry-run (D5) — for Surbhi to read before the patch runs on a server

Command (from the repository on this machine; **ask before running on dev or
production**):

```
docker exec -i <backend-container> bash -s < scripts/brand_text_dry_run.sh
docker exec -i <backend-container> bash -s -- dtc.alvoraa.co < scripts/brand_text_dry_run.sh
```

Or, once this slice's code is on a server: `bench --site <site> execute alvoraa_portal.brand_text.report`.

Output on the local bench (read-only), 27 Sep:

```
=== ppj.localhost
action  setting                                          current_value         proposed
change  Website Settings.app_name                        Frappe                Alvora HRMS
change  System Settings.app_name                         ERPNext               Alvora HRMS
change  Desk Help menu item                              Frappe Support        hidden
change  Desk menu: Switch to Employee Portal (ALV-152)   Route /hrms-employee  Action window.location.assign('/hrms-employee')
report  Emails queued, not sent (keep their old text)    780
```

`test_site` showed the same four changes and 3 queued emails. The 780 on ppj are
local demo mail that was never sent (mail is muted locally).

## 6 · The ALVORA artwork (D2) — done, commit 7a4ff3c

Surbhi's logo arrived on 27 Sep: a 3000 x 3000 JPEG, the purple-to-teal "A" mark
over the ALVORA wordmark, on white.

| Step | Result |
|---|---|
| Master | scaled to 1600 x 1600 (Lanczos, JPEG quality 92, 79 KB) and saved over `alvoraa_portal/brand/alvoraa-logo-master.jpg` |
| `scripts/make_brand_assets.py` | lockup 908 x 627, **mark 720 x 433, split at the blank band** between the mark and the wordmark (the scripts find it by ink, and they did). Mark 128 px 1,963 B; lockup 320 x 221 8,505 B; favicon 32 px 1,153 B |
| `mobile/field-app/scripts/make_app_icons.py` | launcher icons (4 densities, 3 kinds) and 11 splash images redrawn from the mark |
| Phone `web/img/` | the portal's two PNGs copied across; they were byte-identical copies before too |
| Visual check | lockup, mark, 32 px mark and favicon composited on the light (#F8F6F3), dark (#1A1815) and lilac (#F4F1F8) grounds. The mark reads on all three. The purple wordmark is dim on the dark ground, but every place that shows the lockup is light: the desk splash, and the phone sign-in, whose dark theme puts the logo on a #F4F1F8 plate (`app.css` line 142). The launcher icon was checked by eye |
| `brand.py` | `splash_image` → `LOGO`; `banner_image` stays `MARK` (bad news 2); the placeholder comment is gone. `tenant_context.py`'s matching note updated |
| Phone sign-in | `<img class="alv-logo">` back to `img/alvoraa-logo.png`; the "no lockup" test replaced by one that pins lockup-at-sign-in, mark-in-top-bars |
| Live sites | patch `alvora_splash_lockup` runs `brand.apply_site_branding()` - the rule slice 025 already uses: only empty, broken or our own asset paths change; a tenant's upload is left. The dry-run lists all five image slots |

**Browser caching:** nginx serves `/assets/` with `expires 30d, immutable`, and the
file names did not change, so a browser that already holds the old mark can keep
it for up to 30 days. The old and new marks are the same "A" design, so this is
cosmetic.

## 7 · Commands run and what they said

| Command | Result |
|---|---|
| `python scripts/check_brand_spelling.py --self-test` | OK (clean file passes; 9 kinds of mistake caught; exits 1 on a bad file) |
| `python scripts/check_brand_spelling.py` | OK - 41 brand names known, 0 visible, 0 missing translations |
| `python scripts/check_app_integrity.py` | OK - 659 checks |
| `python scripts/check_design_system.py` | OK |
| `ruff check` on every new Python file | all checks passed (the older files keep their existing warnings) |
| `node --test test/*.test.js` (phone app) | **204 pass, 0 fail** |
| `npm run check` (phone app) | OK; versionName 0.3.1, versionCode 30100 |
| `gradlew assembleDebug` with Temurin JDK 21.0.12 | BUILD SUCCESSFUL; `C:\Users\Dell\Downloads\alvoraa\alvoraa-app-0.3.1-debug.apk` (7.1 MB, rebuilt after the artwork swap; its lockup is byte-identical to `web/img/alvoraa-logo.png`) |
| `aapt2 dump badging` | `co.alvoraa.app.debug`, 30100, `0.3.1-debug`, label `Alvora Attendance` |
| dry-run on hrlocal-bench (read-only) | section 5 |
| Full suite on my own site | section 7a |

`npx cap sync android` rewrote two tracked Gradle files with different line endings
only; I restored them. `android/local.properties`, `node_modules` and the synced
assets are git-ignored.

### 7a · The full suite

On my own container `hrlocal-149`, site `test149` (built fresh from the dev image
with erpnext, hrms, alvoraa_portal and alvoraa_goals, its own Redis, the shared
MariaDB). `hrlocal-bench` was not used for tests. The site was migrated first, which
ran `alvora_splash_lockup` (splash_image: ours, now the lockup).

| App | Result |
|---|---|
| alvoraa_portal | **2,538 run: 2,536 pass, 2 fail, 30 skipped** (16 + 819 + 1,703 across Frappe's three batches) |
| alvoraa_goals | **18 run, all pass, 2 skipped** |

The two failures:

| Test | Why it is not this slice |
|---|---|
| `test_review_page_010d.test_decision23_the_card_loads_with_the_screen_and_saves_through_hr_settings` | Asserts `set_org_setting` is absent from the `riSaveSettings` block of `portal.js`. It is present in **`origin/dev`'s** `portal.js` too. Pre-existing |
| `test_shift_types_043.test_my_own_default_shift_is_always_offered` | Expects only its own shift, finds `CI Test Shift`, which `test_checkin_location` creates and leaves on the site. Order and site state; no shift or check-in code is in this slice's diff |

**Browser check** (`scripts/browser_check_brand_menus.js`, Chromium 154, same site,
a probe login with System Manager, HR Manager and an Employee record):

```
ok   portal avatar menu: Switch To Desk is hidden
ok   portal avatar menu: Apps is hidden
ok   portal avatar menu: My Account is still there
ok   portal page: no visible Alvoraa
ok   desk workspace header says Alvora Portal
ok   desk menu: Switch to Employee Portal is there
ok   desk menu: the click lands on the portal  (/hrms-employee)
ok   desk list title says Alvora Position
ok   desk list page: no visible Alvoraa
all checks passed
```

**Negative control:** with the row set back to the old Route type, the same click
stayed on `/desk/alvoraa-portal` - the ALV-152 bug, reproduced in a real browser.
Running the `navbar_portal_switch_as_action` patch made the check pass again.

Found in the browser: in Frappe 16.33.1 the menu opens from the **workspace sidebar
header** (click the workspace name). The user's name at the bottom of the sidebar
only opens their profile. The check opens the menu from a workspace page.

To serve my worktree's CSS, `sites/assets/alvoraa_portal` in my container (a copy
baked into the image) was swapped for a link to the app's `public/` folder. That is
inside my own volume only.

## 8 · Known gaps and shortcuts

| Gap | Label | What removes it |
|---|---|---|
| Dry-run not run on dev or production | **intentional trade-off** - needs Surbhi's word | run section 5's command, show her the list |
| The browser check ran on my local site, not on dev | **temporary debt** | run it against dev after the push |
| `CI Test Shift` left behind by `test_checkin_location` breaks `test_shift_types_043` on a reused site | **temporary debt**, not this slice | a tearDown in `test_checkin_location` |
| Old mark cached in browsers for up to 30 days (`/assets/` is immutable, same file name) | **acceptable simplification** | a new file name, if it matters |
| No Version row for the setting changes | **acceptable simplification** (bad news 4) | switch `_change` to `doc.save()` if wanted |
| Hindi and Punjabi users get their own catalogue, not `en.csv` | **temporary debt** | slice 053's `.po` files; the guard already checks `msgstr` |
| Link values such as the Module Profile "Alvoraa Plan" and invoice item codes | **intentional trade-off** (Surbhi, 27 Sep) | — |
| Frappe's own pages (`/me`, `/update-password`) still show "Apps" and "Switch To Desk" | **acceptable simplification** | a Frappe template override, if ever wanted |
| Desk menu: "Website" and "Switch to Employee Portal" both reach the portal for users with an Employee record | **intentional trade-off** (Frappe hard-codes "Website") | a desk script, if Surbhi wants it gone |
| The "Switch to Employee Portal" row still sits after "Logout", and Frappe ignores its `hidden` box in that menu | **acceptable simplification** | would need a desk script again |
| `copyright` / `brand_html` rewrite needs an exact match; a value like "© 2026 Alvoraa" is left and shown as "leave" in the dry-run | **intentional trade-off** | Surbhi edits it by hand if the dry-run shows one |

## 9 · Surbhi's answers this build follows (27 Sep 2026)

1. Strategy approved. 2. No logo files yet: mark only; swap documented (section 6).
3. The patch may replace "Frappe"/"ERPNext" in `app_name`, exact matches only; the
dry-run list goes to her before any server. 4. The portal avatar menu: hide "Apps"
and "Switch To Desk". 5. "My Account" stays. 6. Hide "Frappe Support" on every
tenant. 7. Invoice item codes and Module Profile names stay "alvoraa". 8. Change
`alvoraa_goals` `app_title`.
