# ALV-174 — email still shows Frappe/ERPNext logos and names

Diagnosis and fix plan only (`CLAUDE.md` §2 steps 1–2). No product code changed yet.
Worktree `.claude/worktrees/alv-174`, branch `fix/alv-174-email-branding`, made fresh
from `origin/dev` (6a31ec1). No collision found on the work board or in incoming
commits for email templates or branding files.

Checked against the installed source inside a throwaway container from the local
image `alvoraa-app:helpdesk-lms-test2` (the most recent local build, carrying CRM,
Helpdesk and LMS). Versions: Frappe v16.35.0, ERPNext v16.36.0 (pinned tags, per
slice 055). No `hrlocal-*` container was touched.

---

## 1. What ALV-149 already fixed, and why the bug is still open

ALV-149 (`alvoraa_portal/alvoraa_portal/brand_text.py` and `brand.py`) already writes,
per tenant, on `after_install` for new tenants and via a patch for existing ones:

- `Website Settings.app_name` → `"Alvora HRMS"` (falls back from `System Settings.app_name`)
- `Website Settings.app_logo` / `banner_image` / `splash_image` / `favicon` → Alvora's
  own PNGs under `/assets/alvoraa_portal/images/`

Two Frappe email functions read exactly these two fields:

- `get_brand_name()` (`frappe/frappe/email/email_body.py:711`) → `Website Settings.app_name`
  or `System Settings.app_name`
- `get_brand_logo()` (`frappe/frappe/email/email_body.py:707`) → the sending Email
  Account's own `brand_logo`, or else `Website Settings.app_logo`

So the **name** in an email header is already "Alvora HRMS" on any tenant the ALV-149
patch has reached. The **logo** and the **footer line** are not — two separate faults,
plus two app-specific ones. Each is below with where it comes from and what a reader
sees.

## 2. Sources found

**A. The footer text "Sent via ERPNext" — every outgoing email, every tenant.**
`erpnext/erpnext/hooks.py:505-512` declares the hook `default_mail_footer`, a fixed
HTML string: `Sent via <a href="https://frappe.io/erpnext...">ERPNext</a>`. Frappe's
own footer template (`frappe/frappe/email/email_body.py:579`,
`templates/emails/email_footer.html`) pulls this hook and prints it on **every**
outgoing email, unless `System Settings.disable_standard_email_footer` is checked.
ALV-149 never touched this switch. This is the one a recipient sees on literally
every email the system sends — leave request notices, payslip alerts, appraisal
reminders, the lot.

**B. The header logo — present, but built as a relative URL, so email clients cannot
load it.** `brand.py` writes `Website Settings.app_logo` as
`/assets/alvoraa_portal/images/alvoraa-mark.png` — no scheme, no host. A browser
resolves that fine against the desk's own page. An email client has no page to
resolve it against, so the `<img src="...">` in `standard.html` (the header only
renders when a caller passes `header=` or `with_container=True` — password reset,
sign-in link, and user invitation) either shows nothing or a broken-image icon in
most mail clients. It is not literally "Frappe's logo" appearing, but it is the same
practical bug Surbhi is reporting: no Alvora mark reaches the inbox. (It does not fall
back to Frappe's own logo, because the stored value is non-empty — the `or
'/assets/frappe/images/frappe-framework-logo.svg'` fallback in `standard.html` only
fires when `brand_logo` is empty.)

**C. Frappe CRM's own invitation email hardcodes "Frappe CRM".**
`crm/crm/templates/emails/crm_invitation.html`: `<p>You have been invited to join
Frappe CRM</p>`, sent whenever an agent is invited to a tenant with the `crm` feature
on. Literal text, not templated from any setting.

**D. Frappe Helpdesk signs its verification email "Team Frappe".**
`helpdesk/helpdesk/templates/emails/macros.html`, macro `signature()`:
```
Thanks,<br />
Team Frappe
```
used by `email_verification.html`, the email an agent gets to confirm their address.
(Helpdesk's other ticket emails — `new_reply_to_agent.html`,
`new_reply_on_customer_portal_notification.html` — sign off "Support Team", no brand
name; those are already fine.)

**E. Frappe LMS's batch/course notifications already source the right field, and
inherit fix B.** `lms/lms/lms/doctype/lms_batch/lms_batch.py:180` and
`lms_course.py:175` read `Website Settings.banner_image` for their own `brand_logo`
context var — the same field `brand.py` already sets to the Alvora mark. Once B is
fixed (absolute URL), these come right for free. No separate LMS fix needed.
LMS's own signature line says "Team School" (not "Frappe") — generic, not a Frappe
brand leak, out of scope for this ticket unless Surbhi wants it renamed too.

**Checked and found NOT to be a source, so left alone:**
- `frappe/frappe/templates/emails/{password_reset,new_user,user_invitation*,
  login_with_email_link,verification_code,workflow_action,new_notification}.html` —
  no hardcoded Frappe/ERPNext text; they all use `app_name`/`brand_name` variables or
  say nothing brand-specific.
- `erpnext.hooks.email_brand_image` — declared, never read anywhere in the installed
  source. Dead hook.
- `erpnext/erpnext/setup/install.py`'s own `default_mail_footer` string — a local
  variable inside that file, never wired to `hooks.py`, never reached. Dead code.
- Website Settings/Navbar Settings logo and `footer_powered`/`copyright` text on the
  **website**, and the desk sign-in/splash screens — already covered by ALV-149
  (`brand.py`, `brand_text.py`); this ticket is about email only.
- No print-format letterhead in `erpnext`/`hrms` carries "Powered by ERPNext" or
  similar text reachable from an email attachment.
- HRMS's own reminder templates (birthday, anniversary, holiday, training, leave
  application) — no brand text; the `frappe.utils.*` calls Grep found are just Jinja
  calling framework helpers, not visible branding.
- Frappe CRM's `hooks.py` (`app_title = "Frappe CRM"`, `app_icon_url`) — used for the
  CRM app's own desk/website chrome, not for outgoing email. Not a source here.

## 3. Why a naive fix is wrong: `get_hooks()` does not override, it appends

`frappe.get_hooks("default_mail_footer")` collects the hook from **every installed
app** into one list and the footer template loops over it
(`{% for line in default_mail_footer %}`). If `alvoraa_portal` declared its own
`default_mail_footer = "Sent via Alvora HRMS"` in `hooks.py`, the result on a tenant
with both apps installed would be a list of two lines — ERPNext's **and** ours, both
printed. Confirmed by reading `frappe.append_hook()`
(`frappe/frappe/__init__.py:1017`): no per-app override semantics exist for a scalar
hook. **The fix is to turn ERPNext's line off, not to add a second one on top of it.**

## 4. Proposed fix

Same pattern ALV-149 already uses — a small module in `alvoraa_portal`, called from
`after_install` (new tenants, day one) and from a patch (existing tenants, on next
migrate), both idempotent and both logged the same way `brand.py` and `brand_text.py`
already are.

**4.1 Kill the ERPNext footer line, per site.**
Set `System Settings.disable_standard_email_footer = 1`. This is the only switch that
actually stops `get_hooks("default_mail_footer")` from being read at all
(`email_body.py:578`) — it is not a value to overwrite, it is a flag to flip. Same
"exact old default only" caution as `brand_text.py` is unnecessary here since there is
only one bit and one meaning; still write it through the same dry-run-first pattern
for consistency and because a tenant may have already set it deliberately (then leave
it, same "ours or theirs" rule as `brand.py`'s `_verdict()`).

**Decision needed — the "Powered by" line.** `System Settings.email_footer_address`
is a free-text field ("Your organization name and address for the email footer"),
rendered in its own `<div class="sender-address">` block, styled the same as the
ERPNext line it would replace. Three options, in order of what I'd recommend:
  a. Leave it blank — no footer line at all. Cleanest, no wording to get wrong.
  b. A plain company line, e.g. the tenant's own company name (we already have it from
     provisioning) — reads like a postal footer, not a "powered by" plug.
  c. "Powered by Alvora HRMS" — matches the wording `brand_text.py` already treats as
     one of Website Settings' defaults, so it stays consistent with the desk.
This needs Surbhi's word before it is built.

**4.2 Make the header logo loadable by an email client.**
Change what `brand.py` writes for `Website Settings.app_logo` (and, for the same
reason, `banner_image` and `splash_image`, since LMS's notifications and any future
caller read `banner_image` too) from a path to a full URL —
`frappe.utils.get_url() + MARK` instead of bare `MARK`. `get_url()` returns each
site's own domain, so a tenant's email logo points at their own subdomain, not a
shared one; stable for as long as the tenant's domain is. Works identically in the
browser (absolute and relative resolve to the same place there) and now also in an
email client, which has no page to resolve a relative path against. `_verdict()`'s
"ours" check (`value.startswith(ASSET_DIR)`) needs to widen to also match
`<site-url>+ASSET_DIR`, so the idempotency guarantee (safe to run twice, and a renamed
asset gets picked up) still holds. `favicon` does not need this — browsers only, no
email path reads it.

**4.3 Frappe CRM's hardcoded invitation text.**
`crm_invitation.html` cannot be edited in place — it lives in the upstream `crm` app,
and editing upstream source is exactly what `frappe-conventions.md` and the CLAUDE.md
rule on upstream changes forbid without an architecture decision. The Frappe-first
mechanism for this is a **template override**: Frappe resolves
`templates/emails/<name>.html` by searching installed apps in reverse hook-order and
takes the first match, so `alvoraa_portal/alvoraa_portal/templates/emails/
crm_invitation.html` (same relative path) is picked up instead of CRM's copy, with no
patch to CRM at all. New file, same shape as the one it replaces, wording changed to
name the tenant / "Alvora HRMS" instead of "Frappe CRM". Only needed on tenants whose
plan includes the `crm` feature — but the override file ships in the app regardless
(it is inert on a tenant without CRM installed), so there is nothing to gate at
provisioning time.

**4.4 Frappe Helpdesk's "Team Frappe" signature.**
Same mechanism: `alvoraa_portal/alvoraa_portal/templates/emails/macros.html`
overriding Helpdesk's copy, with the `signature()` macro's text changed. Lower
priority than 4.1–4.3 — Helpdesk is newly added (slice 166/167, still in another
worktree, not yet sold to a live tenant) — but cheap to include in the same slice
since it is the same override mechanism as 4.3, and it closes the door before
Helpdesk goes live rather than after.

## 5. Coverage: every tenant, the control plane, and future tenants

- **New tenants** — add the new module's setup function to `alvoraa_portal/hooks.py`'s
  `after_install` list, in the same place `brand.after_install` and
  `brand_text.after_install` already sit (provisioning already runs
  `install-app alvoraa_portal`; nothing else to change in `provision_tenant.sh`).
- **Existing tenants** — a patch entry in `patches.txt`, appended at the end (same
  rule as every other patch in that file), so it runs once on the next
  `bench migrate`. Dry-run first, same as `brand_text.py`'s
  `bench --site <site> execute alvoraa_portal.email_brand.report` before anything
  writes.
- **The control plane (alvoraa.co)** — `_is_control_plane()` already exists in
  `brand_text.py` and is the right guard to reuse: the control plane's own outgoing
  mail (billing, tenant admin) is a judgement call for Surbhi — does alvoraa.co's own
  footer/logo also change, or does it stay as-is since it is not a customer-facing HR
  tenant? Flagging this rather than assuming either way.
- **The template overrides (4.3, 4.4)** ship in `alvoraa_portal` itself, so they are
  present for every tenant and every future one the moment the app is installed — no
  per-tenant step at all.

## 6. Test approach

- A unit test for the new module's `plan()`/`apply()` pair, same shape as
  `test_brand_text_*` (if one exists — check during the test-engineer pass) or
  `brand.py`'s own tests: exact-default-only, safe-to-run-twice, "ours or theirs"
  preserved when a tenant already set a footer/logo of their own.
- A rendered-HTML test: call `frappe.email.email_body.get_formatted_html(...,
  with_container=True)` (or the lowest-level function that actually renders
  `templates/emails/email_footer.html`/`standard.html`) against a test site with the
  fix applied, and assert `"ERPNext"` and `"frappe.io"` do not appear, and the `<img
  src=...>` value starts with `https://`.
- A test that renders the overridden `crm_invitation.html` and `macros.html`
  templates and asserts `"Frappe CRM"` and `"Team Frappe"` do not appear, and the
  override actually wins the app-order lookup (install CRM after alvoraa_portal in
  the test site, the same order production uses).
- A one-off manual check: send a real email from a test tenant (password reset is the
  simplest trigger already in the codebase) and open it in an actual mail client, not
  just read the rendered HTML — a relative-URL image bug like B is easy to miss by
  reading markup alone; it only shows up when something actually tries to load it
  with no page context.

## 7. Extending the brand-spelling guard to email templates

`scripts/check_brand_spelling.py` already walks `www`, `templates` and `public/js`
under `APPS = (alvoraa_portal, alvoraa_goals, hrms)` — it does not currently reach
`crm`, `helpdesk` or `lms`, and it checks for the **word** "Alvoraa" (the wrong
spelling of our own name), not for "Frappe"/"ERPNext" appearing where they should not.
Two different jobs. Cheap addition once this fix lands: a second, narrower check (or a
new flag on the same script) that scans our **own** `templates/emails/*` override
files only — the ones this fix adds — for "Frappe" or "ERPNext" as a plain guard
against a future override drifting back to upstream wording when the underlying app
is upgraded and the override file is regenerated by hand. I would not extend the
existing brand-spelling scan to walk the `crm`/`helpdesk`/`lms` app folders themselves
— those are upstream trees we do not own and will keep changing under version
upgrades; the guard belongs on the override files we do own.

## 8. Size

Small. One new module (~2 small functions, following `brand_text.py`'s exact shape),
one `hooks.py` line, one `patches.txt` line, two new small HTML override files, and
their tests. No schema change, no new doctype, no new dependency.

## 9. Decisions needed from Surbhi before this is built

1. **The footer line** (§4.1) — blank, a plain company/site line, or "Powered by
   Alvora HRMS"?
2. **Which logo** for the email header — the mark (small, 128px, already what
   `banner_image`/`app_logo` hold) or the full lockup (`LOGO`, 320px, currently only
   used for the desk splash)? The mark is what the header slot already renders at
   (28px tall in `standard.html`'s `<img height="28">`), so I'd default to the mark
   unless she wants the wordmark specifically legible in an inbox preview pane.
3. **The control plane's own mail** (§5) — same footer/logo change, or left as
   Frappe/ERPNext default since alvoraa.co is not a customer-facing HR tenant?
4. **Helpdesk's fix (§4.4)** — bundle it into this slice now (Helpdesk is not yet
   live) or leave it for slice 166/167 to close since that is the slice that actually
   ships Helpdesk?
