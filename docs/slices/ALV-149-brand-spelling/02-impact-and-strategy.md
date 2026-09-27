---
slice: ALV-149-brand-spelling (plus ALV-152, ALV-153)
status: impact analysis and strategy — WAITING FOR SURBHI'S APPROVAL. No product code changed.
date: 2026-09-27
owner: hrms-fullstack-engineer
reads: 01-product-brief.md, YouTrack ALV-149 (decisions D1-D5 of 27 Sep), ALV-152, ALV-153
frappe: v16.33.1 (read from the local bench, read-only)
---

# ALV-149 · "Alvora" on every screen — impact and strategy

**Bad news first.**

1. **The desk "Switch to Employee Portal" item has never worked on this Frappe version,
   and the fix we shipped on 26 Aug binds to markup nobody can see.** Its tests pass
   because they check the script's text, not the click. Details in Part 2.
2. **Every tenant's desk tab and sign-in email currently say "Frappe" or "ERPNext", not
   our name at all.** Website Settings `app_name` is "Frappe" and System Settings
   `app_name` is "ERPNext" on both local sites. The D5 patch is the place to fix that,
   so it is in the dry-run list below. It widens D5 a little, so it needs your yes.
3. **The new ALVORA artwork will probably not be a pure drop-in.** The cutting script
   finds the monogram by its position in the old master file. New artwork with a
   different layout needs the crop box re-measured. It is still one commit, but not
   zero code.

---

## 0 · What came in, and who else is working here

- `git fetch`: one commit came into `origin/dev` since the brief was branched —
  **a729d61 "The salary screen says what the bank paid…"** (slice 051). It touches
  `hr_api.py` (`_payslip_payload`) and `public/js/ess/portal.js` (the salary block,
  ~lines 2590-2665). My planned edits in those two files are one line each, far from
  that block (`hr_api.py` ~2986, `portal.js` ~3939 and ~12328). I will rebase before
  building.
- **Unmerged branches that touch my files** (from `git log origin/dev..<branch>`):

  | Branch | Overlap | Plan |
  |---|---|---|
  | `slice/041-biometric-sync-user` (6 commits, 23 Sep) | `module_access.py`, `alvoraa_portal/hooks.py` | Sequence: ask you whether 041 is still going to dev. If yes, it goes first and I rebase. My `module_access.py` change is inside `sync_navbar_item` only. |
  | `slice/org-attendance-switches` (built, not pushed) | adds a patch to `alvoraa_portal/patches.txt` | Append-only file. On conflict keep both lines, in commit order. |
  | `slice/034/042/043/044/046-redesign-*` | `hooks.py`, `hr_api.py`, `portal.js`, `ci.yml` | The redesign was discarded on 26 Sep. No action, but whoever revives it must rebase on this. |
  | `053-languages-existing-portal` (brief only) | will add `alvoraa_portal/locale/*.po` | No clash with `translations/en.csv`. The guard must also scan any `.po` file they add (section 5). |

- **Main checkout:** holds another session's uncommitted edit to
  `.claude/context/change-process.md` and many untracked mobile files. Not mine; not
  touched.
- **Other developers:** I cannot see other machines. **Question for you: is anyone
  else working in the portal pages, the phone app's `web/` folder, or `module_access.py`
  this week?**

---

## 1 · Inventory — every occurrence, sorted into "a person reads it" and "only code reads it"

Method: a throwaway classifier over `git ls-files` (docs, `.md`, lock files and images
left out). A line counts as **code** when every match on it is an identifier
(`AlvoraaJoinScreens`, `ALVORAA_X`), a lowercase `alvoraa` (domain, path, app id), or
a quoted doctype / module name used as an argument (`"Alvoraa Position"`). The rest
were then read by hand.

**Totals:** 1,189 lines in 304 files. **~920 are code** (leave alone), 61 comments or
docstrings, 20 copyright headers, **188 candidate visible lines**. After reading them,
**about 95 lines in 24 files are real screen, email or message text.** The rest are
docstrings the classifier could not recognise, log titles, and test data.

| Area | Visible lines to change | Files | Examples | Code lines left as they are |
|---|---|---|---|---|
| Portal `www` pages: login, admin console, enrol | 16 | `alvoraa-login.html`, `alvoraa-admin.html`, `alvoraa_admin.py`, `enrol.html`, `hrms_employee_next.py` | login footer "© Alvoraa", tenant name fallback "Alvoraa", admin title "Tenant Admin – Alvoraa", "Open the Alvoraa app to use this code" | route names `/alvoraa-login`, `/alvoraa-admin` |
| Portal ESS templates | 0 | — | the ESS page shows the tenant's name, not ours | — |
| Portal public JS | 8 | `employee_field_app.js` (6), `ess/portal.js` (2) | "Install **Alvoraa** from the Play Store", "Your Alvoraa app code", "Ask your Alvoraa account contact" | `alvfe*` names |
| Python messages users see (`frappe.throw`, `_()`, email subjects) | 12 | `field_app_join.py` (4, incl. the "new phone signed in" **email subject and body**), `field_app_alerts.py`, `hr_api.py`, `alvoraa_operations_pack.py:52`, `alvoraa_data_review_item.py:96`, `invoicing.py:181` and `:301`, `www/alvoraa_admin.py:24` | "…is an Alvoraa HR feature", "reset it on your company's Alvoraa website" | 247 lines of doctype names in code |
| Default tenant name | 1 | `tenant_context.py:22` | `"tenant_name": "Alvoraa"` — shown on the login page and in page titles when a site has no name | — |
| Subscription feature label | 1 | `subscription.py:1027` | `"label": "Alvoraa HR"` → "Alvora HRMS" | key `alvoraa_hr` stays |
| Phone app web screens | 27 | `web/index.html` (13), `js/checkin.js` (3), `js/checkin-screens.js` (2), `js/join.js`, `js/join-screens.js` (2), `js/signin-core.js` (3), `js/strings.js` ("Powered by Alvoraa") | `<title>Alvoraa Attendance</title>`, `alt="Alvoraa"`, error texts | header `X-Alvoraa-App-Version`, `window.Alvoraa*` |
| Phone app sign-in **lockup image** | 1 | `web/index.html:34` `img/alvoraa-logo.png` | shows the ALVORAA wordmark (D2) → switch to `alvoraa-mark.png` | file names stay |
| Android launcher and Capacitor | 3 | `strings.xml` `app_name`, `title_activity_main`; `capacitor.config.json` `appName` | "Alvoraa Attendance" → "Alvora Attendance" | `package_name`, `custom_url_scheme`, `appId` = `co.alvoraa.app` |
| hooks `app_title` | 2 | `alvoraa_portal/hooks.py:2`, `alvoraa_goals/hooks.py:2` | shown in Help → About and in boot app data | `app_name` stays |
| **Desk: doctype names** | 33 names | 33 doctype folders (25 in `alvoraa_portal`, 5 in `alvoraa_goals`, 4 in the `hrms` fork) | "Alvoraa Position", "Alvoraa Subscription", "Alvoraa Pricing Settings" in list titles, breadcrumbs, search | the names themselves never change |
| **Desk: module names** | 8 names | `modules.txt` × 3 | "Alvoraa HR Core", "Alvoraa Late Rules", "Alvoraa Goals", "Alvoraa Portal" … | same |
| **Desk: workspace** | 1 | `workspace/alvoraa_portal/alvoraa_portal.json` (`label`, `title`) | sidebar title and desktop tile "Alvoraa Portal" | workspace `name` |
| Doctype field labels and descriptions | **0** | — | none carries the brand (checked every `label`/`description` in doctype JSON) | 23 Link `options` |
| Report names, print formats, Email Templates, Notifications | **0** | — | the two reports and the web form do not carry the brand; no print format or email template is shipped with it | — |
| Invoices (control plane only) | 1 + 5 item codes | `invoicing.py:181` remarks "Alvoraa subscription for {period}" | item **codes** "Alvoraa Platform Fee" etc. are record names — see §3.6 | — |
| Module Profile names | 2 records | `module_access.py:31-32` "Alvoraa Plan", "Alvoraa Plan (HR)" | seen only by admins on the User form | record names — see §3.6 |
| Website / Navbar / System Settings, Email Account | tenant **data**, not code | see §3.4 | Website `app_name` "Frappe", System `app_name` "ERPNext" on both local sites | — |
| PWA manifest | **0** | none in our apps; the Frappe HR PWA (`/hrms`) is Frappe-branded and out of scope | — | — |
| Boot info | **0** | no `boot_session` / `extend_bootinfo` hook in our apps | — | — |
| Tests that assert the old text | ~45 | `mobile/field-app/test/*.test.js`, a few Python tests | updated with the code they check | — |
| Not user-facing, left alone | — | copyright headers (20), `setup.py` descriptions, `deploy/provision_tenant.sh` banner, `nginx.conf` comment, docstrings, log titles such as `"Alvoraa: could not write jobs file"` | — | — |

**Size of the text change: about 95 lines of code text in 24 files, plus about 45
lines of test expectations.** Much smaller than the ~700 matches suggested, because
most matches are doctype names used as code.

---

## 2 · How the desk labels change — the part that needed checking (D4)

**Verified in the installed source: Frappe 16.33.1 does apply English
"translations".**

- `frappe/translate.py` `get_all_translations(lang)` has **no early exit for English**.
  It merges, for every installed app, `translations/<lang>.csv`
  (`get_translations_from_csv`, lines 172-193) and the compiled `.mo` files. `en-GB` and
  `en-US` fall back to `en` (`get_parent_language`).
- Python `_()` (`frappe/utils/translations.py:25`) and JavaScript `__()`
  (`public/js/frappe/translate.js:17`, fed from `bootinfo["__messages"]`,
  `boot.py:234`) both look strings up in that dictionary.
- The desk draws doctype and workspace names through `__()`: the sidebar header
  (`ui/sidebar/sidebar_header.html:11`, `__(workspace_title)`), the desktop tile
  (`ui/desktop_icon.html:19`, `__(icon.label)`), list titles and breadcrumbs.

**Recommended route: one file, `alvoraa_portal/translations/en.csv`,** about 45 rows:
`Alvoraa Position,Alvora Position`, one per doctype, module and workspace name, plus
the two Module Profile names if you want them. It lives in `alvoraa_portal` because
that app is on every tenant and owns the brand. It covers the `hrms` fork's four
doctypes and six modules without touching the fork.

Routes I rejected:

| Route | Why not |
|---|---|
| Rename the doctypes | Breaks every link, permission hook, patch and test that names them (~920 lines). The brief already said no. |
| Property Setter on a doctype "label" | A DocType has no label property in v16 to set. |
| Per-tenant `Translation` records | Tenant data. Would need a patch on every site, and a tenant could delete them. |
| Change the workspace JSON `title` | Not needed — the translation covers it, and changing a synced record's JSON is one more conflict surface. |

**What the translation does not reach**, and what I will check on a throwaway site
before calling it done:

- URLs keep the old slug (`/desk/alvoraa-position`). That is by the rule.
- A user whose language is **Hindi or Punjabi** gets the `hi`/`pa` catalogue, not
  `en`. When slice 053 adds those, its `.po` files need the same names. The guard
  (§5) checks this.
- Link **values** (a Module Profile named "Alvoraa Plan" shown in a Link field) are not
  translated. Only admins see these. §3.6.
- Help → About lists app titles without `__()`. That is why `app_title` changes too.
- Anything I cannot prove on the throwaway site, I will list, not guess.

**Cache:** translations are cached in Redis (`MERGED_TRANSLATION_KEY`) and in each
browser's boot data. The deploy's `bench migrate` clears the Redis cache. Open desk
tabs keep the old words until the user reloads. No extra step is needed.

---

## 3 · The strategy, piece by piece

### 3.1 Screen, email and message text — direct edits

Straight text edits in the 24 files in §1. Every edited user-facing string stays
wrapped in `_()` / `__()` / `drT()`. No sentence is built by joining pieces. The rule
from the brief holds: **"alvoraa" survives only inside a web address, an email
address, a path, an id or code.**

Two cases to note:

- `tenant_context.py:22`: default tenant name "Alvoraa" → "Alvora". This is the
  fallback when a site has no `tenant_name` in `site_config.json`. Real tenants have
  their own name, so it shows only on unconfigured sites and the control plane.
- `subscription.py:1027` label "Alvoraa HR" → "Alvora HRMS" (D3). The key
  `alvoraa_hr` stays, because plans and tests use it.

### 3.2 Product name, D3: "Alvora HRMS"

- `alvoraa_portal/hooks.py:2` `app_title = "Alvora HRMS"`.
- `alvoraa_goals/hooks.py:2` `app_title = "Alvora Goals"`. **One line in
  `alvoraa_goals`; no behaviour.** I checked the risk: Frappe makes an app desktop icon
  from `app_title` only for apps with `add_to_apps_screen`
  (`desktop_icon.py:275-298`), and neither of our apps has that. So no duplicate icon
  appears. If you would rather keep `alvoraa_goals` completely untouched, say so; the
  only cost is "Alvoraa Goals" in Help → About.
- The desk tab title and the sign-in email use Website Settings `app_name`, then
  System Settings `app_name` (`www/desk.py:61`, `www/login.py:53`,
  `email/email_body.py:712`). Those are tenant data — §3.4.

### 3.3 The logo, D2 — mark only now, one-step swap later

- **Now:** the phone app's sign-in screen (`mobile/field-app/web/index.html:34`) shows
  `img/alvoraa-mark.png` instead of `img/alvoraa-logo.png`, with `alt="Alvora"`. The
  portal already shows only the mark (`brand.py` `SLOTS`). Nothing else displays the
  lockup.
- **When your files arrive:**
  1. Save the master as `alvoraa_portal/brand/alvoraa-logo-master.png` (the file name
     is the contract, so it keeps the old spelling).
  2. Run `scripts/make_brand_assets.py` and `mobile/field-app/scripts/make_app_icons.py`.
     **Expect to re-measure the crop box**: both scripts find the monogram by its
     position in the old master. If you can send the mark and the lockup as two
     separate files, the crop step goes away.
  3. Put `LOGO` back in the two `SLOTS` rows of `brand.py` (lines 99-100) and in
     `index.html:34`.
  4. Portal: new image and deploy. Phone: the next app build.

  That is one commit, and I will write these steps into the implementation notes.

### 3.4 Tenant settings, D5 — dry-run first, then the patch

**The rule:** rewrite a value **only if it is exactly one of our known old defaults**.
Anything a tenant typed stays. This is the same "ours or theirs" rule `brand.py`
already uses.

| Setting | Replace when the value is exactly | With | Why it matters |
|---|---|---|---|
| Website Settings `app_name` | "", "Frappe", "ERPNext", "Alvoraa", "Alvoraa HR", "Alvoraa HRMS" | "Alvora HRMS" | desk tab title, sign-in page, emails. **"Frappe"/"ERPNext" are Frappe's defaults, not ours — replacing them is a small widening of D5. Your call.** |
| System Settings `app_name` | the same list | "Alvora HRMS" | fallback for the above |
| Website Settings `brand_html`, `copyright`, `footer_powered`, `title_prefix` | a value where "Alvoraa" is the only change needed (e.g. "Alvoraa", "© Alvoraa") | the same with "Alvora" | web page header and footer |
| Email Account `email_account_name` | exactly "Alvoraa", "Alvoraa HRMS", "Alvoraa HR" | "Alvora …" via `frappe.rename_doc` | **the From name**: Frappe sends `email_account.name` as the sender name (`email_body.py:323-325`). The address `noreply@alvoraa.co` does not change. |
| `site_config.json` `tenant_name` | exactly "Alvoraa" | **report only** | a file, not a record. I will not write site files from a patch. |
| Queued emails (`Email Queue`, status Not Sent) | — | **report only: a count** | already built with the old text; they go out as they are. Production mail is muted until go-live, so this should be zero. |

**How it runs:**

1. **Dry-run, before any push.** A read-only script,
   `scripts/brand_text_dry_run.sh`, runs `bench --site <s> mariadb -e "select …"` on each
   site and prints: site, setting, current value, proposed value, or "left alone:
   typed by the tenant". It needs **no new code on the server**, so it can run against
   today's dev and production images. **Running it on dev and production is a server
   command, so I will ask you first, every time.** The output goes into this slice's
   notes for you to read.
2. **You approve the list.**
3. **The patch** (`alvoraa_portal/patches/v1_0/alvora_brand_text.py`, appended to
   `patches.txt`) runs at the deploy's `migrate` with the same exact-match rule. If a
   value changed between the dry-run and the deploy, it no longer matches and is
   left alone, so the patch can never overwrite something you did not see. It prints
   one line per change: site, setting, old, new — no personal data. Saving the singles
   through the ORM also leaves a Version row, so each change can be traced and undone.
4. **New tenants:** the same function runs from `after_install`, next to
   `brand.after_install`, so a new site starts as "Alvora HRMS".
5. It **refuses on the control plane** for Email Account renames (that site is ours;
   you rename it by hand if you want) and runs the rest there too.

### 3.5 The Navbar item (ALV-152) — see Part 2. It needs its own small patch.

### 3.6 Things I recommend leaving as "alvoraa", for you to overrule

| Item | Who sees it | Why leave it | Cost to change |
|---|---|---|---|
| Invoice item **codes** "Alvoraa Platform Fee" and four more (`invoicing.py:40-44`) | customers, on control-plane invoices | They are Item record names. Invoices already issued keep the old ones. The line description is already brand-free. | rename 5 Items on the control plane with `rename_doc`; ~10 lines |
| Module Profile names "Alvoraa Plan", "Alvoraa Plan (HR)" | tenant admins, on the User form | Record names that `module_access.py` looks up. | a rename patch on every tenant; medium risk. Adding them to `en.csv` does **not** help (Link values are not translated). |
| Doctype URL slugs `/desk/alvoraa-position` | anyone who reads the address bar | It is a URL — allowed by the rule | — |
| "Frappe Support" and "About" in the desk Help menu | every desk user | Frappe's own, and not a spelling issue | see Part 2, §B.4 |

---

## 4 · The CI guard — `scripts/check_brand_spelling.py`

Same style as `check_tag_balance.py` and `check_preview_flag.py`: plain Python, no
dependencies, `--self-test`, one step appended to the lint job in `ci.yml`.

**What it scans:**

- `alvoraa_portal/**/www/*.html`, `templates/**/*.html`, `public/js/**/*.js`
  (HTML and JS comments stripped first);
- `mobile/field-app/web/**` (html, js), `android/**/res/values*/strings.xml`,
  `capacitor.config.json`;
- **Python in all three apps, by parsing it (`ast`)**: string literals passed to
  `_()`, `frappe.throw`, `frappe.msgprint`, and `subject=` / `message=` of
  `frappe.sendmail`. Parsing means docstrings, comments and log titles are skipped
  without a hand-kept list.
- `hooks.py` `app_title`;
- `translations/en.csv` and any `locale/*.po`: the right-hand side / `msgstr` must not
  contain "Alvoraa".

**What it fails on:** `Alvoraa` or `ALVORAA` in visible text.

**The allow-list is computed, not hand-kept:**

- lowercase `alvoraa` anywhere (domains, paths, ids, `co.alvoraa.app`);
- identifiers — the match is part of a longer word (`AlvoraaJoinScreens`, `ALVORAA_X`,
  `X-Alvoraa-App-Version` as a header name);
- a quoted string that is **exactly** a doctype, module or workspace name, read at run
  time from the doctype JSON files and `modules.txt`. Exactly, not "contains": so
  `"Alvoraa Pricing Settings"` as an argument passes, but
  `_("Set 'Invoice From' in Alvoraa Pricing Settings.")` fails, because the desk now
  calls it "Alvora Pricing Settings".
- a short named list for the rest (the test-only leave types, the two Module Profile
  names if you keep them), each with a one-line reason.

**The completeness check:** every doctype, module and workspace name that contains
"Alvoraa" must have a row in `translations/en.csv`. So a new `Alvoraa Something`
doctype cannot reach the desk under the old spelling.

**`--self-test`** writes temporary files and proves it fails on: "Alvoraa" in a
template, in a `frappe.throw`, in `strings.xml`, and a doctype missing from `en.csv`.
It passes on: a domain, an identifier, a doctype name used as an argument, and a
comment. I will also break it once on purpose in a real file, to see CI go red.

---

## 5 · Non-functional impact — ALV-149 (with ALV-152/153)

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **improves (slightly)** | ~45 rows join the boot translation dictionary (under 3 KB, cached). The 2-second poll in `portal_switch.js` goes away with the ALV-152 fix. No new queries on any page. |
| Security | **neutral** | No new endpoint, no permission change. The Navbar item keeps the same audience. It becomes an Action string, which is the same trust level as Frappe's own "Reload" item. Hiding menu items (ALV-153) is not treated as a permission; the desk is still guarded by module profiles on the server. |
| Reliability | **neutral** | The patch is exact-match and safe to run twice. A failure on one setting logs and moves on; it never blocks `migrate`. The guard adds a CI step that can only fail the build, not the app. |
| Scalability | **neutral** | Nothing grows with headcount. The Email Account rename updates Link fields on `Communication` once, per tenant. |
| Maintainability | **improves** | One brand rule enforced by CI instead of by memory. `portal_switch.js`, which was wrong and pinned by misleading tests, is deleted. |
| Data integrity | **neutral** | Only exact old defaults change. Every change leaves a Version row. The dry-run shows you the list first. Queued emails keep their old text (reported, not touched). |
| Compliance / privacy | **neutral** | No personal data is read, logged or shown. The field-app notice text does not name the company, so the notice version "2026-09-22" and every acknowledgement stay valid (brief §1, checked again). The patch prints setting names and values only. |

## 6 · Cross-module and persona impact

| Module | Impact |
|---|---|
| `alvoraa_portal` | All text edits, `en.csv`, the patch, the guard, ALV-152/153. |
| `alvoraa_goals` | **One line** (`app_title`), optional — §3.2. No behaviour. |
| `hrms` fork | **Untouched.** Its four doctypes and six modules get their desk labels from `alvoraa_portal/translations/en.csv`. |
| `erpnext`, `crm`, `frappe` | **Untouched.** |
| Phone app | Strings, launcher label, sign-in mark. Rides the next build; no special build (brief). `co.alvoraa.app` unchanged, so it installs over 0.3.0 without signing anyone out. |
| HRMS domain (leaves, attendance, payroll, appraisals, org) | No logic changes. Only the words around them. |

| Persona | What changes |
|---|---|
| **CXO** | Sees "Alvora" on the portal, login, emails and desk labels. No data or scope change. |
| **HR Manager** | Same, plus desk labels ("Alvora Position"), the tab title "Alvora HRMS", a working "Switch to Employee Portal", and a shorter avatar menu on the portal. |
| **Employee** | Portal, login, emails and phone app say "Alvora". On the portal, the avatar menu no longer offers a way into the desk that the server would refuse (ALV-153). |

## 7 · Risks

| Risk | What could go wrong | How it is handled |
|---|---|---|
| String-match false positives | The guard flags code, or a mass replace changes an identifier | No mass replace. Every edit is by hand from the §1 list. The guard's allow-list is computed from the doctype JSON, so it cannot drift. |
| String-match false negatives | Text built at run time ("Alvor" + "aa") | None found. The guard catches the literal forms we use. |
| Translation cache | Desk still shows old labels after deploy | `migrate` clears Redis; users reload once. I will check both on the throwaway site. |
| Translation reach | A label drawn without `__()` keeps the old name | Checked on the throwaway site, screen by screen. Anything left is listed, not hidden. |
| Hindi / Punjabi users | They get their own catalogue, not `en` | The guard checks `.po` files when 053 adds them. |
| Tenant overrides | The patch overwrites a value a tenant chose | Exact-match only; dry-run first; Version row per change. |
| Email Account rename | Links to the old name break | `frappe.rename_doc` updates Link fields. It runs only on exact old defaults, after you approve the row. |
| Emails already queued | Go out with "Alvoraa" | Counted in the dry-run. Should be zero (mail muted until go-live). |
| Old phone builds | Show "Alvoraa Attendance" until updated | Accepted in the brief. |
| Trademark | "Alvora" is ruled out later | Screen text is cheap to reverse: `en.csv` and the edits are one revert. |

---

# Part 2 · The two desk user-menu bugs

## A · ALV-152 — "Switch to Employee Portal" does nothing

**Root cause: our click handler is bound to a menu that is never shown.**

1. We add the item as data: a Navbar Settings row of type **Route**, route
   `/hrms-employee` — `alvoraa_portal/module_access.py:1071-1095` (the row is built at
   lines 1086-1091).
2. Frappe 16.33.1 builds the visible menu with
   `frappe.ui.create_menu({menu_items: this.dropdown_items})` —
   `frappe/public/js/frappe/ui/sidebar/sidebar_header.js:334-342`. That renderer
   (`frappe/public/js/frappe/ui/menu.js`) draws each item as
   `<div class="dropdown-menu-item" onclick="return <item.action>">` (**line 102-104**)
   and, when the item has no `url`, handles a click with
   `item.onClick && item.onClick()` (**lines 126-129**).
3. A **Route** row from Navbar Settings has a `route`, but **no `url`, no `action` and
   no `onClick`**. `add_navbar_items()` only copies the label across
   (`sidebar_header.js:106-111`). So the click runs nothing, the menu closes, and the
   user stays in the desk. No error — which is why it looks like it "does not switch".
4. Our fix of 26 Aug (`d871f8b`) binds to
   `.dropdown-menu-item[data-app-route="/hrms-employee"]` —
   **`alvoraa_portal/public/js/portal_switch.js:30-31`**. That attribute is written
   only by the older `add_app_item()` (`sidebar_header.js:351-353`), which appends to
   `.sidebar-header-menu`. **The v16 template `sidebar_header.html` has no
   `.sidebar-header-menu` element**, so those items go nowhere. The selector matches
   nothing on the page, every 2 seconds, forever (`portal_switch.js:64-67`).
5. The tests in `tests/test_module_access.py:519-580` read the script's *source text*
   ("contains `data-app-route`") rather than the menu, so they pass. The same gap
   affects Frappe's own "Apps" row where it exists (from Frappe's patch
   `v16_0/add_app_launcher_in_navbar_settings.py`) — every Route row in that menu is
   dead in this version.

Proof, read-only: the Navbar Item rows on `ppj.localhost` and `test_site` are
`Delete Demo Data` (Action) and `Switch to Employee Portal` (Route, `/hrms-employee`).
I did not click it in a browser. The cause is proven from the installed source and the
local data.

**Fix plan — use the one item type Frappe's menu does run:**

1. `sync_navbar_item()` writes the row as **Action**, with
   `action = "window.location.assign('/hrms-employee')"` (single quotes only, because
   `menu.js` puts it inside a double-quoted `onclick`). It **upgrades an existing Route
   row in place** (same label) instead of returning early, and still never adds a
   second row.
2. A small patch, `patches/v1_0/navbar_portal_switch_as_action.py`, calls it on every
   tenant, because `sync_navbar_item()` otherwise runs only at provisioning and plan
   change (`module_access.py:218`, from `sync_site`). The patch **only updates a row
   that already exists** — it never adds one — so the control plane, which has no
   row, is untouched.
3. Delete `public/js/portal_switch.js` and its `app_include_js` entry
   (`alvoraa_portal/hooks.py:67-69`). Nothing else uses it.
4. Replace the three source-text tests with tests that check behaviour.

Known limits, unchanged by this fix: the item still appears **after "Logout"**, because
Frappe appends Navbar Settings items to the end (`sidebar_header.js:100`). And Frappe
ignores the row's `hidden` tick box in this menu. Moving or hiding it would need a desk
script again, which is the thing we are removing.

**Tests (named, so a bad merge cannot drop them):**

- `test_alv152_navbar_item_is_an_action_that_opens_the_portal` — after
  `sync_navbar_item()` there is exactly one row, type Action, and its action opens
  `/hrms-employee` and contains no double quote.
- `test_alv152_an_old_route_row_is_upgraded_not_duplicated` — insert the old Route row,
  run the sync and the patch twice, still exactly one Action row.
- `test_alv152_patch_never_adds_a_row` — no row before, none after.
- `test_alv152_frappe_menu_still_runs_action_items` — pins
  `onclick="${item.action ? \`return ${item.action}\` : ""}"` in Frappe's `menu.js`.
  If a Frappe upgrade removes it, this fails before users notice.
- `test_alv152_portal_switch_script_is_gone` — not in `app_include_js`, file absent.
- **Browser check** on the throwaway site (the `scripts/browser_check_*.js` pattern): log
  in as an HR user with an Employee record, open the menu, click the item, and land on
  `/hrms-employee`.

## B · ALV-153 — "Apps" and "Switch to Desk" go to the same place

**Where this menu is:** "Switch to Desk" does not exist in the desk's own menu in
v16. It exists only in **Frappe's website navbar**, the avatar menu at the top right of
web pages — and **our Employee Portal renders that navbar**:
`www/hrms-employee.html:1` extends `templates/web.html` and does not override the
navbar block (`frame.css:30` pins it to the top). `[ASSUMPTION]` This is the menu you
saw. Please confirm, or tell me the page.

**Root cause: two Frappe links to one page.**

- `frappe/templates/includes/navbar/navbar_login.html:17` — "Switch To Desk", href
  `/desk`. Shown for any login with the `system_user` cookie
  (`frappe/website/js/website.js:638-639`).
- `navbar_login.html:18` — "Apps", href `/apps`. Shown when an installed app's
  apps-screen route is **not** under `/desk` (`website.js:620-634`,
  `frappe/apps.py:63-68`). On a tenant with **CRM** installed (route `/crm`), that is
  true. On the local sites, which have no CRM, "Apps" stays hidden — which is why it
  depends on the tenant.
- `frappe/hooks.py:70` — `{"source": "/apps", "target": "/desk"}`. **In v16 `/apps`
  simply redirects to `/desk`.** So "Apps" and "Switch To Desk" land on the same
  screen.

**The whole-menu check — every door on the portal page and in the desk:**

| Where | Item | Goes to | Duplicate of |
|---|---|---|---|
| Portal, avatar menu (Frappe) | My Account | `/me` (Frappe's profile page) | — (the portal has its own profile; see question 5) |
| Portal, avatar menu (Frappe) | Log out | `/logout` | — |
| Portal, avatar menu (Frappe) | Switch To Desk | `/desk` | **the portal sidebar's own switch** |
| Portal, avatar menu (Frappe) | Apps (CRM tenants) | `/apps` → `/desk` | **Switch To Desk** |
| Portal, sidebar (ours, `frame.html:101`) | Switch to Admin / Switch to HR Core | `/app` → `/desk`, `/app/hr` → `/desk/hr` (`module_access.py:1099-1115`) | Switch To Desk (for admins) |
| Desk menu (Frappe) | Desktop | `/desk` | — |
| Desk menu (Frappe) | Website | opens `/` in a new tab → **`/hrms-employee` for anyone with an Employee record** (`auth.py:13-52`) | **Switch to Employee Portal** |
| Desk menu (ours) | Switch to Employee Portal | `/hrms-employee` (after the ALV-152 fix) | Website |
| Desk Help menu (Frappe) | Frappe Support | `https://frappe.io/support` | — but it is Frappe-branded and sends staff to Frappe |

A second problem hides in the first: **Frappe's "Switch To Desk" ignores our rule.** Our
own sidebar switch asks the server (`get_switch_target`) and stays hidden for employees
"who have no business there". Frappe's link shows for every System User login. If an
employee's login is a System User, the portal offers them a desk the server will then
block. `[ASSUMPTION — to check on the throwaway site]`

**Fix plan (recommended): one door per place, and it is ours.**

1. On portal pages, hide Frappe's **"Apps"** and **"Switch To Desk"** in the avatar menu
   with two selectors in `public/css/ess/frame.css` (`#website-post-login .apps`,
   `#website-post-login .switch-to-desk`). Our sidebar switch, which the server decides,
   stays the only way into the desk from the portal. No new file, no hook, no JS.
2. Frappe's own pages outside our portal (`/me`, `/update-password`) keep Frappe's
   menu. I recommend living with that: our users rarely go there, and changing it means
   overriding a Frappe template. Say if you want it anyway.
3. Desk menu, "Website" vs "Switch to Employee Portal": both hard-coded or data we
   cannot filter without a desk script. **Recommendation: keep both.** "Website" is
   Frappe's, opens a new tab, and is not always the portal (a default workspace or a
   role home page changes it). Say if you want "Website" gone; it costs a small desk
   script.
4. "Frappe Support" in the Help menu: Help items do respect `hidden`, so a one-line
   addition to the D5 patch can hide it on every tenant. **Your call** — it is not a
   duplicate, but it is Frappe branding in front of a customer.

**Tests:**

- `test_alv153_portal_hides_frappe_desk_links` — `frame.css` contains both selectors
  with `display:none` (a pin test; a bad merge that drops them fails CI).
- A DOM test in `alvoraa_portal/tests/` (jsdom, run by `scripts/run_dom_tests.js`):
  render the avatar menu markup from `navbar_login.html` with `frame.css`, un-hide it
  the way `website.js` does, and check that neither link is visible.
- Browser check on the throwaway site, as an HR user and as an employee: the avatar menu
  shows My Account and Log out only; the sidebar switch still works for HR.

---

## 8 · Order of work and size

**Size: medium — about 2.5 working days to build and test, then review.** One slice,
one worktree, one push to dev when you say so.

| Step | What | Estimate |
|---|---|---|
| 1 | Guard in report mode, so it lists every hit and drives the edits | 0.5 day |
| 2 | Text edits: portal www, admin console, login, enrol, public JS, Python messages, `tenant_context`, invoice remarks, `subscription.py` label | 0.5 day |
| 3 | Phone app: strings, `strings.xml`, `capacitor.config.json`, sign-in mark; update the JS tests | 0.25 day |
| 4 | `translations/en.csv`, the `app_title` lines; check every desk screen on a throwaway site | 0.25 day |
| 5 | Tenant text: dry-run script, patch, `after_install`, tests. **Dry-run on dev and production only with your OK** | 0.5 day |
| 6 | ALV-152 and ALV-153 with their tests and browser checks | 0.25-0.5 day |
| 7 | Guard switched to failing, CI step, the break-it-once proof; full suite once, in my own container | 0.25 day |

The bench: I will use **my own throwaway container and site** (not `hrlocal-bench`),
claim it on the work board, and run the full suite once at the end.

The dtc go-live window: all of this fits before the first week of October if you
approve by 29 Sep. The part that must land before go-live is steps 2, 4, 5 and 6. The
phone strings (3) ride the next app build.

---

## 9 · What I need from you

1. **Approve this strategy**, or change it.
2. **Your ALVORA artwork.** Where are the files — a Drive link, or attach them to ALV-149?
   Best: **PNG, at least 1600 px, transparent or white background, and the mark and the
   full lockup as two separate files.** A vector (SVG/PDF) is even better for later.
3. **D5 widening:** may the patch also replace Frappe's own defaults ("Frappe",
   "ERPNext") in `app_name` with "Alvora HRMS"? Recommended: yes.
4. **ALV-153:** confirm the menu you saw is the avatar menu at the top right of the
   Employee Portal. And confirm the fix: hide Frappe's "Apps" and "Switch To Desk" on
   the portal, keep our sidebar switch.
5. **Portal avatar menu, "My Account"** goes to Frappe's `/me` page, not the portal's
   profile. Keep, hide, or point to the portal profile? Recommended: hide it on the
   portal, in the same CSS rule. (Not in scope unless you say so.)
6. **"Frappe Support"** in the desk Help menu: hide it on every tenant? Recommended: yes.
7. **§3.6:** leave invoice item codes and the two Module Profile names as "alvoraa"?
   Recommended: yes, for now.
8. **`alvoraa_goals` app_title:** change the one line? Recommended: yes.
9. **Is `slice/041-biometric-sync-user` still going to dev?** It touches
   `module_access.py` and `hooks.py`.
10. **Is anyone else working** in the portal pages, the phone app's `web/` folder, or
    `module_access.py` this week?

## Assumptions

- `[ASSUMPTION]` ALV-153's "user menu" is Frappe's avatar menu on the Employee Portal.
- `[ASSUMPTION]` Employee logins on at least some tenants are System Users, so they see
  Frappe's "Switch To Desk" (checked on the throwaway site before building the fix).
- `[ASSUMPTION]` The From name of tenant emails comes from the Email Account name
  (`email_body.py:323-325`), unless the code passes its own sender name. The dry-run
  shows each tenant's accounts.
- `[ASSUMPTION]` The legal entity (AllAboutHR) is unchanged; `app_publisher` stays.
