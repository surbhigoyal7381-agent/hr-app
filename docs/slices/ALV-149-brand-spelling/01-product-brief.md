---
slice: ALV-149-brand-spelling
status: draft for Surbhi's decision
date: 2026-09-27
owner: hrms-product-manager
---

# ALV-149 · Brand spelling: "Alvora" on every screen

**Bad news first. (1) The "Alvora" trademark search is still not done** (product-context §10, risk 7). Changing every screen is cheap to undo now and expensive after dtc goes live. **(2) Users will see "Alvora" next to web addresses that read `alvoraa.co`.** You chose that, and it is fine. But expect the question "is this the real site?" and prepare HR at dtc for it.

This brief is thin on purpose: a copy and brand change, with no competitive analysis and no Kano. There is no UX scan (`01a`) or DevOps note (`07`) behind it.

## 1 · The rule

**If a person can read it on a screen, in an email or on a phone, it says "Alvora". If only code, a machine or our own staff read it, it may say "alvoraa".** An error message shown to a user counts as a screen (for example `alvoraa_operations_pack.py` line 52: "…is an Alvoraa HR feature").

| Changes to "Alvora" | Stays "alvoraa" |
|---|---|
| Portal, login and enrol pages, ESS screens, admin console text | Python packages, app names (`alvoraa_portal`, `alvoraa_goals`) |
| Phone app text: sign-in, join, check-in (31 files in `mobile/field-app`, Confirmed) | Doctype and module *names* in the database |
| Android launcher label and `appName` ("Alvoraa Attendance" today, Confirmed) | Application id `co.alvoraa.app` (changing it breaks updates) |
| Browser tab titles, page meta and descriptions | Domains, URL paths, email addresses and sender domains |
| Email subject, body and the **From name** | Log titles, code comments, test names, docs |
| Messages shown by `frappe.throw` / `msgprint` | JS identifiers such as `window.AlvoraaJoinScreens` |

**The tricky cases:**

- **Doctype and module names in the desk.** HR managers see "Alvoraa Position", "Alvoraa Reporting Line", and module names such as "Alvoraa HR Core". Renaming doctypes is risky and not needed. *Recommendation:* change the displayed label with an English translation shipped in the app. **Needs validation:** the engineer must prove Frappe applies English translations to doctype labels in our version. If it does not, leave the desk as it is for now.
- **Email From name versus address.** The name changes and the address does not. `Alvora <noreply@alvoraa.co>` is correct. The From name lives in each tenant's Email Account record `[ASSUMPTION — engineer to confirm]`, so it is tenant data, not code.
- **Tab title and PWA name.** The tab titles change. I found no PWA manifest in `alvoraa_portal` (Confirmed). I did not check the Frappe HR mobile front end, which is branded "Frappe HR" and is out of scope.
- **Android launcher label.** It changes to "Alvora Attendance" in the next app build. Phones on the old build keep the old label until they update. That is acceptable.
- **The phone app notice.** **No new notice version is needed.** The notice text in `field_app_notice.py` does not name the company (Confirmed by search). The current version, "2026-09-22", and every acknowledgement already given stay valid. The rule for later: if a future notice names the company, that is a new version, not an edit. **I am not a lawyer.** If counsel wants the controller's legal name in the notice, that is a separate decision.
- **SEO and meta.** Change the titles and descriptions. The URLs stay, so nothing breaks.
- **Existing tenant data** (Website Settings app name, title and footer; Navbar Settings; Email Account name) on dtc, ppj, sargam and the dev tenants. *Recommendation:* one patch that rewrites a value **only if it is exactly our old default**, and leaves anything a tenant typed alone. This is the same "ours or theirs" rule `brand.py` already uses.

## 2 · The logo

The current master reads ALVORAA and is a placeholder (`brand.py` line 86). **Until the real artwork exists, show the "A" mark only, everywhere.** The portal already does this. The phone app 0.3.0 sign-in shows the full ALVORAA lockup, so it must switch to the mark.

**Who makes the artwork?** *Recommendation: you, or a designer you pick, provide a vector master.* We then regenerate the files with `scripts/make_brand_assets.py` and put `LOGO` back in the two `SLOTS` rows of `brand.py`.

The trade-off: we *can* render "ALVORA" from an open-licence font in an afternoon. But a logo is a brand decision, and a stopgap wordmark tends to become the permanent one. Use the font route only if you want a wordmark before go-live, and then you choose the font.

## 3 · Slices and order

dtc goes live in the first week of October, so there are about five working days.

**Slice A: before dtc goes live.** Everything a dtc employee or HR manager meets:
- the portal, login and ESS screens, tab titles, emails and user-facing errors;
- the tenant-data patch;
- the mark only, in the portal and the phone app;
- the guard in §4.

The phone app strings and launcher label ride in the next build dtc staff install. Do not cut a special build for this. **Evidence required:** the engineer must size this. There are about 700 matches in `alvoraa_portal` alone, many of them code that must *not* change.

**Slice B: after go-live.** Desk labels through translations, print formats and reports, and the real artwork swap.

## 4 · The guard

A CI check, `scripts/check_brand_spelling.py` with a `--self-test`, in the same style as the checks already in `ci.yml`. It scans only user-facing files: `www/`, `templates/`, `public/js/`, `mobile/field-app/web/`, `strings.xml`, `capacitor.config.json`, and email, notification and print-format JSON. It fails on `Alvoraa` or `ALVORAA` in visible text.

The allow-list covers lowercase `alvoraa` (domains, paths, ids), identifiers like `AlvoraaSomething`, and a named list of doctype names used as code arguments. Break it on purpose once, to prove it can fail.

## 5 · Acceptance criteria

1. On a dtc copy, the login, portal, ESS screens, tab titles and phone app screens say "Alvora". "alvoraa" appears only inside a web or email address.
2. An email to an employee shows "Alvora" as the From name and in the text. The address is unchanged.
3. No screen shows the ALVORAA lockup.
4. The new app build shows "Alvora Attendance" on the launcher. It installs over 0.3.0 without signing the user out.
5. The notice version is unchanged, and no user is asked to agree again.
6. A value a tenant typed in Website Settings survives the patch.
7. The guard fails when "Alvoraa" is added to a template, and passes on domains and identifiers.
8. No package, doctype, URL or app id changed, and the existing tests pass.

## 6 · Decisions for Surbhi

| # | Decision | My recommendation |
|---|---|---|
| D1 | Go ahead before the trademark search on "Alvora" is done? | Yes for screens (easy to reverse). Hold artwork spend until the search is done. |
| D2 | Who supplies the ALVORA artwork? | You or your designer, as a vector file. The mark only until then. |
| D3 | Product names: "Alvora HR" and "Alvora Attendance"? | Yes, a straight swap. |
| D4 | Desk doctype and module labels before go-live? | No. Slice B, through translations. |
| D5 | Rewrite existing tenant settings automatically? | Yes, only exact old defaults, with the list shown to you before it runs. |

## Open questions

- **Does dtc's HR team work in the desk or only the portal?** Owner: Surbhi. Blocks: whether D4 can wait.
- **Is there a separate legal entity name for notices and invoices?** Owner: Surbhi and counsel. Blocks: the invoice and notice wording.

## Assumptions

- `[ASSUMPTION]` "Alvora" is the brand name only. The legal entity, AllAboutHR, is unchanged.
- `[ASSUMPTION]` The email From name comes from each tenant's Email Account record.
- `[ASSUMPTION]` The admin console is seen by our staff and customers' admins, so it counts as user-facing.

## Kill criteria

Stop if the trademark search rules out "Alvora", or if the go-live week cannot absorb Slice A without risk to dtc.
