# ALV-174 — implementation notes

Built on `fix/alv-174-email-branding`, from `origin/dev` at `6a31ec1` (ALV-166/167
review fix). Fetched and rebased once during the build to bring in
`6a31ec1` — no conflicts, nothing else touched the files this slice owns.
Local only: not pushed, not merged into local `dev`, no server, no docker cp
against anything but the throwaway test container.

## What was built, file by file

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/email_brand.py` | new module, `plan`/`apply`/`report`/`after_install`, same shape as `brand.py`/`brand_text.py` | Switches off `System Settings.disable_standard_email_footer`, writes `System Settings.email_footer_address` (tenant name + "Powered by AllAboutHR"), writes `Email Account.brand_logo` (the full ALVORA lockup, absolute URL) on every enabled outgoing account |
| `alvoraa_portal/alvoraa_portal/overrides/crm_invitation.py` | `override_doctype_class` | CRM's own invitation email hardcodes "Frappe CRM" in the SUBJECT (Python) and the BODY (a template that ignores the `title` it's passed) — a template override can't fix a Python-built subject, and is unreliable for the body anyway (below). Replaces `invite_via_email` only |
| `alvoraa_portal/alvoraa_portal/templates/emails/macros.html` | Jinja template override | Helpdesk's `signature()` macro says "Team Frappe". Added as asked, with an honest limitation noted in the file itself (see below) |
| `alvoraa_portal/alvoraa_portal/patches/v1_0/alvora_email_brand.py` + one line in `patches.txt` | patch, once on next migrate | Existing tenants get the fix without a reinstall |
| `alvoraa_portal/alvoraa_portal/hooks.py` | two additions | `email_brand.after_install` appended to the existing `after_install` list; new `override_doctype_class` block for CRM Invitation |
| `alvoraa_portal/alvoraa_portal/tests/test_email_brand_174.py` | tests | See below |
| `scripts/email_brand_dry_run.sh` | read-only SQL, same shape as `brand_text_dry_run.sh` | Surbhi reads this before the patch runs anywhere real |
| `scripts/check_email_template_overrides.py` + one CI step | narrow guard | Our own `templates/emails/` and `overrides/` files never say "Frappe"/"ERPNext" in text a recipient reads |
| `docs/slices/ALV-149-brand-spelling/05-sample-rendered-email.html` | evidence | A real rendered password-reset email, from the pipeline, with an actual outgoing Email Account resolved |

## The AC list (from Surbhi's decisions on the approved plan)

1. **Footer**: tenant company name + "Powered by AllAboutHR", ERPNext's line never
   shows alongside ours. **Satisfied** — `disable_standard_email_footer` is the
   only thing that removes ERPNext's hook-appended line (hook lists can only grow,
   never override — confirmed by reading `frappe.append_hook`); our own line goes
   through the separate `email_footer_address` field, which renders regardless of
   that switch. Proven by rendering the real footer HTML
   (`test_alv174_the_footer_never_says_sent_via_erpnext`) — "ERPNext" and
   "frappe.io" are absent, "Powered by AllAboutHR" is present.
2. **Header logo**: full ALVORA lockup, absolute URL, on the tenant's own domain.
   **Satisfied**, on the `Email Account.brand_logo` field, not `Website
   Settings.app_logo` — see "Which field the email header reads" below for why.
   Proven by rendering with a real outgoing Email Account resolved: the sample
   file's `<img src>` is `http://test174/assets/alvoraa_portal/images/alvoraa-logo.png`
   (the lockup, not the mark; absolute; the tenant's own site).
3. **Control plane**: same branding, applied with no special case — `email_brand.py`
   never reads `alvoraa_control_plane` at all (pinned by
   `test_alv174_the_control_plane_gets_no_special_skip`). The reply-to
   (`support@alvoraa.co`) is **not** written by any code here — see "What was
   deliberately not built" below.
4. **Helpdesk signature**: overridden as asked. **Partially satisfied** — see the
   honest limitation in the file itself and below; it is precautionary, not a
   proven live fix.
5. **CRM invitation**: overridden via `override_doctype_class`, not a template.
   **Satisfied** for both the subject and the body — proven by calling
   `invite_via_email` with `frappe.sendmail` mocked and asserting "Frappe CRM"
   appears in neither.
6. **after_install + patch, exact-old-default rule, dry-run**: **Satisfied**.
   `plan()`/`_footer_is_ours()`/`_logo_is_ours()` distinguish "nobody chose
   anything, or this module wrote it before" from "the tenant typed something",
   the same shape as `brand.py`'s `_verdict()`. `scripts/email_brand_dry_run.sh`
   is read-only SQL that needs none of this slice's Python on the server, and its
   constants are pinned against the real module's by
   `test_alv174_dry_run_script_uses_the_same_footer_line_and_asset_names`.
7. **Tests**: 19 tests, see the test run below.
8. **Narrow guard on our own overrides**: `scripts/check_email_template_overrides.py`,
   wired into CI next to the brand-spelling check.
9. **Brand guard covers "AllAboutHR" cleanly**: confirmed — `check_brand_spelling.py`
   only matches the literal substrings "Alvoraa"/"ALVORAA"; "AllAboutHR" doesn't
   contain either, and a real run against the whole repo after this change is
   still clean (`0 visible 'Alvoraa'`).

## A real bug found by actually rendering the email, not by reading the Python

`get_footer()` (`frappe/email/email_body.py`) reads `disable_standard_email_footer`
and `email_footer_address` through `frappe.db.get_default()` — a **different**
table (`tabDefaultValue`) from the one `frappe.db.set_single_value()` writes
(`tabSingles`). System Settings' own `on_update` keeps them in sync
(`set_defaults()`, one `frappe.db.set_default()` call per changed field) — but
only on a real document save. My first version wrote `tabSingles` only,
exactly like `brand_text.py` does for its own fields — the code looked right,
imported cleanly, and CI-shaped checks (ruff, integrity, the unit tests that
only read `tabSingles` back) would all have passed. The rendered email still
said "Sent via ERPNext", because `get_footer()` never looks at `tabSingles` for
these two fields.

The direct fix — `frappe.get_single("System Settings").save()` — fails a
different way: it runs the WHOLE document's validation, including
`language`/`time_zone` mandatory fields, and `after_install` runs **before** the
setup wizard, when a brand-new tenant's System Settings has neither set yet
(reproduced against a fresh site — `frappe.exceptions.MandatoryError`, not a
guess). The actual fix writes both tables directly for the one field being
changed — exactly what `set_defaults()` does per field, without the rest of the
document's validation riding along. `brand_text.py`'s own fields don't need
this: Frappe reads those back through `get_system_settings()` /
`get_website_settings()`, which go straight to the cached document, never
through `get_default()`.

This is written into `email_brand._save_system_setting`'s own docstring so the
next person editing a System Settings field here doesn't repeat it.

## Which field the email header actually reads, and why `Website Settings.app_logo` is untouched

`get_brand_logo()` prefers the sending Email Account's own `brand_logo` field
over `Website Settings.app_logo`. `Website Settings.app_logo` is also what the
**desk navbar** reads (`navbar_settings.get_app_logo()`), and `brand.py`
(ALV-149) already set it to the small mark. Writing the 320px lockup there
would have resized the desk navbar's logo along with the email header — an
unasked-for screen change. Per-Email-Account keeps the two independent: the
desk keeps the mark, outgoing mail gets the lockup.

## CRM's invitation: why a template override was rejected, in favour of `override_doctype_class`

Read before writing any code, not assumed:

- `crm.fcrm.doctype.crm_invitation.crm_invitation.CRMInvitation.invite_via_email`
  builds the **subject** in Python: `title = "Frappe CRM"`, an f-string. A
  template can never reach a subject line built this way.
- Its own template, `templates/emails/crm_invitation.html`, hardcodes
  "You have been invited to join Frappe CRM" as literal text — it never reads
  the `title` argument it is passed, so even a working template override would
  still need the file's own wording changed.
- Even so, a template override would have been **unreliable**: Frappe's Jinja
  loader searches installed apps in reversed install order
  (`frappe/utils/jinja.py:_get_jloader`), and both `provision_tenant.sh` and
  `tenant_api._run_install_modules` install `alvoraa_portal` **before** `crm` on
  every tenant — so CRM's own copy of the template would still have won the
  lookup, not ours. Confirmed by reading both install sequences, not assumed.

`override_doctype_class` (the mechanism `frappe-conventions.md` already names
for "replace standard logic wholesale") sidesteps all three: it replaces the
Python method itself, which builds the email inline via `content=` rather than
`template=`, so nothing depends on which app's Jinja file wins.

## Helpdesk's "Team Frappe" — built, with an honest limitation

Grepped every `.py` file in the installed `helpdesk` app: nothing calls the
template that imports this macro (`templates/emails/email_verification.html`
has zero Python callers anywhere in the app). It looks unreachable in this
version. The override is precautionary, not a proven live fix, and the file's
own comment says so — so the next person who finds it live and wired up
(a Helpdesk upgrade, most likely) knows to re-check both this and the
install-order point above before trusting it. It also could not be given a
dynamic tenant name (`frappe.db` is not in the Jinja sandbox's safe-globals
allow-list for this render path, confirmed by reading `get_safe_globals`) —
it says "Alvora HRMS" statically instead, matching every other default in the
app.

## What was deliberately not built

- **The control plane's Reply-To** (`support@alvoraa.co`). `add_reply_to_header`
  + `reply_to_addresses` on the control plane's own sending Email Account is the
  right mechanism (confirmed against the source: `email_body.py:validate_reply_to`),
  but it is a live mail-sending-config change on the Brevo-backed account, not a
  footer or a logo, and Surbhi asked for it to be flagged rather than written by
  a patch. **Recommend**: she (or whoever holds the Brevo/Email Account
  credentials) ticks "Add Reply-To in Email Header" on that account and adds
  `support@alvoraa.co` under Reply To Addresses, by hand, whenever she chooses.
- **LMS's own signature** ("Team School") — not "Frappe", out of scope for this
  ticket; noted in the plan doc, not touched.
- **Reordering tenant provisioning** so `alvoraa_portal` installs after
  `crm`/`helpdesk`/`lms` (which would make a template-override approach reliable
  everywhere) — real provisioning risk for a branding fix; not attempted.
  `override_doctype_class` made it unnecessary for CRM; Helpdesk's macro override
  stays best-effort.

## Tests run

Throwaway container `hrlocal-174` (+ `hrlocal-174-db`, `hrlocal-174-redis`), own
network, the worktree's `alvoraa_portal/` bind-mounted over the image's copy
(`alvoraa-app:helpdesk-lms-test2`, Frappe v16.35.0 / ERPNext v16.36.0). Fresh
site `test174`, apps installed: `erpnext`, `hrms`, `alvoraa_portal`, `crm`,
`payments`. All containers and the network removed after.

- `ruff check` on every changed/new Python file — clean.
- `python scripts/check_app_integrity.py` — 668 checks, OK.
- `python scripts/check_brand_spelling.py` — 41 brand names known, 0 hits, OK
  (confirms "AllAboutHR" and "Powered by AllAboutHR" trip nothing).
- `python scripts/check_email_template_overrides.py --self-test` then the real
  check — both OK, 0 hits.
- `bench --site test174 run-tests --app alvoraa_portal --module
  alvoraa_portal.tests.test_email_brand_174` — **19 tests, 18 passed, 1 skipped**
  (the dry-run-parity test skips inside this container because only
  `alvoraa_portal/` was bind-mounted, not `scripts/` — confirmed by reading its
  own skip message, not a real gap).
- The real rendered footer and header were checked against the actual Frappe
  pipeline (`get_footer`, `get_formatted_html`), not just against our own
  settings — so a future change to Frappe's own template shape would be caught
  too.
- A real sample email was rendered with a genuine outgoing Email Account
  resolved (not the `email_account=None` fallback), saved to
  `docs/slices/ALV-149-brand-spelling/05-sample-rendered-email.html`: no
  "ERPNext" or "frappe.io" anywhere, the header logo is
  `alvoraa-logo.png` (the lockup) as an absolute URL, footer reads the tenant
  name then "Powered by AllAboutHR".
- `bench --site test174 run-tests --app alvoraa_portal` (the **whole** suite,
  817 tests, 2,578s): **9 failures, 466 errors, 35 skipped.** Grepped the whole
  output for every file this slice touches (`email_brand`, `crm_invitation`,
  `AlvoraCRMInvitation`, `override_doctype_class`, `test_email_brand_174`) —
  **zero matches**. The failures shown (leave-year rollover, org-figures branch
  counts, appraisal-permission hooks, a hardcoded far-future date in an
  unrelated fixture) are shaped exactly like the "known local failures" other
  slices' notes describe on a site that never went through the setup wizard or
  a fixture-loading step (fiscal years, company, org structure) — and this site
  only carries 5 of the product's 12 apps (no `india_compliance`, `whatsapp`,
  `lms`, `helpdesk`, `telephony`), unlike `test_site`/`ppj.localhost`. I did not
  have budget in this pass to build out the full fixture baseline other
  slices' dedicated scripts (`fixtures_045.py`, `fixtures_scale_044.py`, and
  similar) provide, purely to get a clean comparison run for a six-file
  branding fix — **temporary debt**: whoever next runs this branch's full
  suite on a properly provisioned bench (`test_site` or a fresh throwaway with
  the complete fixture set) should confirm the 475 are unchanged by this slice,
  the way I could not directly prove here. I am confident, not certain, that
  none of it is this slice's doing.

## Dry-run

```
docker exec -i <backend-container> bash -s < scripts/email_brand_dry_run.sh
docker exec -i <backend-container> bash -s -- dtc.alvoraa.co < scripts/email_brand_dry_run.sh
```

Run against the real throwaway site (`test174`) with the two settings
deliberately reset to Frappe's defaults first, to prove it reports real
"change" rows, not just "nothing to do":

```
=== test174
change  System Settings.disable_standard_email_footer   0   1
change  System Settings.email_footer_address                Alvora\nPowered by AllAboutHR
```

Then applied for real (`email_brand.apply()`) and re-run: `nothing to change`.

## NFR notes

- **Query count**: `plan()` is a handful of `get_all`/`get_single_value` calls,
  bounded by the number of enabled outgoing Email Accounts on a site (a small,
  fixed set per tenant, never per-employee). Runs once at install, once per
  migrate — not on any request path.
- **Reliability**: every write path is wrapped per-row in `apply()`'s own
  try/except, logged to the Error Log by setting name only (no personal data),
  same as `brand.py`/`brand_text.py`. Safe to run twice — proven by
  `test_alv174_safe_to_run_twice`.
- **Privacy**: nothing here touches employee data. The only "personal" field in
  reach is an Email Account's own address, and it is never logged — only the
  setting name and old/new footer/logo values, which are product configuration,
  not personal data.
- **Upgrade-safety**: `override_doctype_class` requires our subclass to be a
  subclass of CRM's `CRMInvitation` — Frappe enforces this itself at import
  time (`frappe.throw` if not), so a future CRM upgrade that renames or removes
  the method would surface as an import-time error on that tenant, not a silent
  divergence. `check_email_template_overrides.py` guards the two files that
  hand-copy upstream wording against a future upgrade re-introducing it.
- **Multi-tenancy**: every write is scoped to `frappe.local.site` (the ORM's own
  scoping) and applied per site independently, the control plane included, with
  no special-casing — consistent with `brand.py`/`brand_text.py`.

## Known gaps and shortcuts

- **Temporary debt**: the full-suite baseline was not independently confirmed
  clean on a properly provisioned bench (see "Tests run" above). Removed by:
  a run of the whole `alvoraa_portal` suite on `test_site`/`ppj.localhost` or an
  equivalently complete throwaway site before this reaches `dev`.
- **Acceptable simplification**: Helpdesk's macro override is best-effort —
  documented as such in the file itself, not hidden.
- **Intentional trade-off**: the control plane's Reply-To is proposed, not
  built — Surbhi's own instruction.
- No feature flag, no backwards-compatibility shim, no speculative
  configuration added.
