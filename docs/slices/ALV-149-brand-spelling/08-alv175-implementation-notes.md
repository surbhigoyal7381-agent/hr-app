# ALV-175 — implementation notes

Built on `fix/alv-175-email-logo`, from `origin/dev` at `6dec8b6` (ALV-174).
Local only: not pushed, not merged into local `dev`, no server, no docker cp
against anything but the throwaway test container.

## The gap ALV-174 left open

`email_brand.apply()` only writes `brand_logo` on Email Accounts with
`enable_outgoing = 1`. On sargam.dev (dev-6dec8b6) there is no such account,
so mail resolves to the server's virtual "Notifications" account instead,
which has no `brand_logo` field to set at all. `get_brand_logo()` then falls
back to `Website Settings.app_logo` - a relative path, deliberately left
alone by `apply()` because the desk navbar reads that same field and a 320px
lockup there would resize it. Relative URLs don't load in a mail client, so
no logo reaches the inbox. The footer is unaffected (it doesn't depend on
which account sent).

## What was built

| File | Mechanism | Why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/templates/emails/standard.html` | Jinja template override (new) | Frappe's `templates/emails/standard.html` is the ONE place every email's header logo is drawn, whichever account sent it - the one place that can close this regardless of the account problem |
| `alvoraa_portal/alvoraa_portal/email_brand.py` | new function `resolve_header_logo()` | Called from the template; "ours or theirs" rule reusing the existing `_logo_is_ours()` helper: empty or one of our own known asset paths (relative or absolute) becomes the absolute lockup, anything else (a tenant's own deliberate logo) is untouched |
| `alvoraa_portal/alvoraa_portal/hooks.py` | one line in the existing `jinja.methods` list | Registers `resolve_header_logo` as a Jinja global, the same mechanism this app already uses for `ess_part` |
| `alvoraa_portal/alvoraa_portal/tests/test_email_logo_175.py` | tests | See below |
| `scripts/check_email_template_overrides.py` | `--check-upstream-shape` (new) | Compares the sha256 declared in `standard.html`'s own comment against Frappe's ACTUALLY INSTALLED file, so an upgrade that reshapes it is caught, not silently shipped |
| `.github/workflows/ci.yml` | one new step, in the job that already builds a real bench | Runs `--check-upstream-shape` where `BENCH_APPS_PATH` actually points at real Frappe source |
| `docs/slices/ALV-149-brand-spelling/07-alv175-sample-no-account-email.html` | evidence | A real rendered email, from a site with NO outgoing Email Account at all |

## Confirmed before writing any template code, not assumed

**Our copy wins the template search on every tenant.** Frappe's Jinja loader
searches installed apps in REVERSED install order
(`frappe/utils/jinja.py:_get_jloader`). Unlike ALV-174's CRM case, there is no
install-order ambiguity here: `frappe` is always the very first app on any
Frappe site - enforced by the framework itself, not a provisioning choice
that could get it wrong. `alvoraa_portal` is always installed after it, so it
is always searched first. Proven three ways, not just argued:
- Asked Jinja directly which file it resolved:
  `get_jenv().get_template("templates/emails/standard.html").filename` came
  back pointing at `apps/alvoraa_portal/alvoraa_portal/templates/emails/standard.html`,
  never `apps/frappe/frappe/templates/emails/standard.html`.
- Pinned as `test_alv175_standard_html_resolves_to_our_own_copy`.
- The rendered sample email (below) itself only makes sense if our copy won -
  Frappe's own template has no `resolve_header_logo` call to make.

## What changed in the template, and what didn't

Identical to Frappe v16.35.0's own `standard.html` (sha256
`fd3e883de26cc12aa10f723e36bdc5ab9ebae160fcaa91fd62913a8c4f0ddf88`, read from
the installed image, not typed from memory) except:
- One `{% set resolved_logo = resolve_header_logo(brand_logo) %}` line added
  after `<body>`.
- `brand_logo` replaced with `resolved_logo` in the two places the original
  template reads it (the outer `{% if %}` and the `<img src>`).

Nothing else moved - same structure, same classes, same the dead
`'/assets/frappe/images/frappe-framework-logo.svg'` fallback string kept
verbatim (genuinely unreachable either way, in both the original and this
copy, since the surrounding `{% if %}` only enters when the value is already
truthy - not this slice's problem to fix). The explanation of all this lives
in a **Jinja** comment (`{# ... #}`), not an HTML one, specifically so none of
it - including the upstream sha256 - ever reaches a real email; Jinja strips
`{# #}` blocks before rendering.

## The upstream-shape guard

`check_email_template_overrides.py --check-upstream-shape` reads the sha256
declared in `standard.html`'s own comment, finds the real installed
`frappe/frappe/templates/emails/standard.html` via `BENCH_APPS_PATH` (same
probing `check_app_integrity.py` already uses), and compares. Proven both
ways in the throwaway container, not just the passing case:
- Ran it against the real installed file: **matches, OK.**
- Tampered with the real installed file (appended a line), ran it again:
  **caught, FAIL, exit 1**, with a message naming both hashes. Restored the
  file afterward.
- Also covered without needing Docker at all: `self_test()` now builds a
  fake "upstream" file and a fake override in a temp directory, points
  `BENCH_APPS_PATH` at it, and proves both the pass and the fail case
  directly against `check_upstream_shape()` - this is what actually runs in
  CI's `--self-test` step, so the guard's own logic is pinned even in the
  no-bench job.
- Wired into `.github/workflows/ci.yml`, in the job that already builds a
  real bench for `check_app_integrity.py`'s doctype-shadowing check (the only
  place `BENCH_APPS_PATH` points at real Frappe source, not a placeholder).

## A tenant's own deliberate logo is never overridden

`resolve_header_logo()` only replaces a value that is empty or matches one of
our own known asset paths (`_logo_is_ours()`, unchanged from ALV-174 - reused,
not duplicated). Anything else - a tenant's own uploaded logo on their sending
Email Account, or a custom `Website Settings.app_logo` - passes through
untouched. Proven by rendering with a real Email Account carrying a
deliberately different `brand_logo`
(`test_alv175_a_tenants_deliberate_account_logo_still_wins`): the rendered
HTML contains their URL, not ours.

## Tests run

Throwaway container `hrlocal-175` (+ `hrlocal-175-db`, `hrlocal-175-redis`),
own network, the worktree's `alvoraa_portal/` bind-mounted over the image's
copy (`alvoraa-app:helpdesk-lms-test2`, Frappe v16.35.0). Fresh site
`test175`, apps installed: `erpnext`, `hrms`, `alvoraa_portal` (no `crm` this
time - not needed for this fix; the three CRM-specific ALV-174 tests skip
cleanly, as designed). All containers and the network removed after.

- `ruff check` on every changed/new file - clean.
- `python scripts/check_app_integrity.py` - 669 checks, OK.
- `python scripts/check_brand_spelling.py` - 0 hits, OK.
- `python scripts/check_email_template_overrides.py` (text scan) - 0 hits, OK.
- `python scripts/check_email_template_overrides.py --self-test` - OK,
  including the two new upstream-shape cases.
- `bench --site test175 run-tests --app alvoraa_portal --module
  alvoraa_portal.tests.test_email_logo_175` - **11 tests, 10 passed, 1
  skipped** (the CI-wiring check skips inside this container only, because
  `scripts/` wasn't bind-mounted - confirmed by its own skip message).
- `bench --site test175 run-tests --app alvoraa_portal --module
  alvoraa_portal.tests.test_email_brand_174` (the ALV-174 module, re-run
  against the files this slice also edited - `hooks.py`, `email_brand.py`) -
  **19 tests, 15 passed, 4 skipped** (the 3 CRM-specific tests plus the
  dry-run-parity test skip cleanly - `crm` isn't installed on this site and
  `scripts/` isn't mounted; no regression).
- `--check-upstream-shape` run for real against the installed bench: passes
  clean, then tampered and caught (see above).
- A real sample email rendered with **no outgoing Email Account passed at
  all** - the exact shape of the Sargam bug - saved to
  `docs/slices/ALV-149-brand-spelling/07-alv175-sample-no-account-email.html`:
  `<img src="http://test175/assets/alvoraa_portal/images/alvoraa-logo.png" ...>`
  - absolute, the full lockup, no `alvoraa-mark.png`, no
    `frappe-framework-logo`.

Did **not** re-run the whole `alvoraa_portal` suite this time. ALV-174's build
already ran it in full (817 tests, 9 failures/466 errors, all confirmed
unrelated to either slice's files) and documented why a from-scratch
throwaway site without the full fixture baseline is a noisy comparison; that
finding still applies unchanged here, and repeating a 43-minute run for a
two-file, template-and-one-function change would not have added evidence
this instruction asked for. If that's wanted before this reaches `dev`, say
so and I'll run it.

## NFR notes

- **Performance**: `resolve_header_logo()` is one string check against two
  known suffixes, called once per rendered email header. No query.
- **Reliability**: pure function, no side effects, cannot fail an email send.
- **Privacy**: touches no personal data.
- **Upgrade-safety**: the whole point of this slice - the guard fails loudly,
  in CI, the moment Frappe's own file reshapes, rather than silently serving
  a stale copy after an upgrade.
- **Multi-tenancy**: `frappe.utils.get_url()` returns the CURRENT site's own
  domain, so the logo URL is always the tenant's own, never shared or
  hardcoded.

## Known gaps and shortcuts

- **Acceptable simplification**: did not re-run the full `alvoraa_portal`
  suite in this pass - see "Tests run" above for why, and the standing
  ALV-174 finding it relies on.
- No feature flag, no backwards-compatibility shim, no speculative
  configuration added.
