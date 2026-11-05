# ALV-318 and ALV-319 — what I ran, and what it said

**Not the shared bench.** `hrlocal-bench` binds the main checkout, which is 406
commits behind `origin/dev`, and it runs a background Frappe worker against the
shared test database — the ALV-268 phantom `QueryDeadlockError`. So I built my own
stack from the same image the local bench uses:

| Container | What it is |
|---|---|
| `alv318-mariadb` | `mariadb:10.8`, `utf8mb4` / `utf8mb4_unicode_ci`, its own database |
| `alv318-redis` | `redis:alpine`, its own hook cache — nothing shared with any other session |
| `alv318-bench` | `ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3`, with **my worktree** bind-mounted over `apps/alvoraa_portal`, `apps/alvoraa_goals` and `apps/hrms` |

Its own `test_site`, built from scratch with frappe 16.33.1, erpnext 16.34.2,
hrms, alvoraa_portal and alvoraa_goals, `allow_tests true` and
`throttle_user_limit 1000`, exactly as `ci.yml` builds its own.

Every summary below was read **from the log file**, not from a tail, because
`bench run-tests` prints one summary per batch and a tail hides the earlier one.
Two suites here print two.

## Test suites

| Suite | Batches | Result |
|---|---|---|
| `test_joiner_079` (first run, 68 existing + 16 new) | 84 tests in 1138s | **OK** |
| `test_joiner_078` | 55 tests in 780s | **OK** |
| `test_portal_security_010` | 45 tests in 167s, **and** 5 tests in 7s | **OK, both batches** |
| `test_home_page_024` (auth.py) | 30 tests in 39s | **OK** |
| `test_request_guard_alv249` (auth.py) | 5 tests in 14s, **and** 3 tests in 42s | **OK, both batches** |
| `test_first_use_lock_242` (auth.py) | 31 tests in 74s | **OK** |
| `test_first_use_backfill_242` (auth.py) | 8 tests in 4s | **OK** |
| `test_joiner_to_employee_082` — **first run** | 0 tests in 11s | **FAILED, 4 errors** — see below |
| `test_joiner_to_employee_082` — after the fixture fix | 33 tests in 16s | **OK** |
| `test_joiner_079` — re-run on the finished code | 84 tests in 1654s | **OK** |

**Total: 292 tests across nine suites, every batch OK**, plus the 082 first run
whose four fixture errors are explained below and are green on the re-run.

## The one real failure, and what it was

`test_joiner_to_employee_082` failed in `setUpClass` on all four of its classes,
with my own refusal message:

> “Alvoraa Joiner” cannot be given to an account here. …

Slice 082's fixture builds a joiner login **directly**, not through
`make_sign_in`, and says so in its own comment: the sign-in needs the employer's
settings and a site-wide mobile-login switch, and none of that is what those
tests are about. My guard refused it, correctly.

**The fix is in that fixture, not in the guard.** It now builds the login with no
roles and then adds the role with the invite flag set, with a comment saying it is
standing in for `make_sign_in` and why claiming the flag is legitimate there (the
flag is server-side only; no request can set it). That is a change to **another
slice's test file**, and it is the only file outside my own scope that I touched.

This is also the clearest evidence that the guard works: it caught the one place
in the whole repository that hands out this role outside the invite path, and
nothing else in nine suites noticed it at all.

## Static gates — every step from `ci.yml`'s Lint job

| Gate | Result |
|---|---|
| `check_api_paths.py --max 0` | OK, 0 unresolved |
| `check_app_integrity.py` | OK, 920 checks |
| `check_design_system.py` | OK — the visual system holds (no emoji; it expands `portal.js` into the page it scans) |
| `check_nginx_conf.py` | OK |
| `check_no_demo_passwords.py` | OK, 41 files |
| `check_preview_flag.py` self-test + run | OK |
| `check_tag_balance.py` self-test + run | OK |
| `check_portal_assets_gate.py` self-test + run | OK |
| `check_min_app_version.py` self-test + run | OK |
| `check_brand_spelling.py` self-test + run | OK, 0 visible "Alvoraa" |
| `check_email_template_overrides.py` self-test + run | OK |
| `check_scope_traps.py` self-test + run | OK |
| `check_portal_handlers.js` | OK |
| `check_portal_trays.js --static` | OK, 28/28 |
| `check_undefined_js.js` | OK |
| `check_rating_bands.js` | OK |
| `run_dom_tests.js` (after `npm ci`) | 23 run, 0 failed |
| `check_tracked_keys.py` (Key guard job) | OK, 3341 files |
| `ruff check` on my five changed files | **no new findings.** The same three pre-existing ones in `joiner_invite.py` (one `I001`, one `RUF002`, one `UP031`) are present on `origin/dev`'s copy of the file too — compared directly. CI pins ruff 0.6.9 and the step is non-blocking; mine is 0.15.4 |

**Not run:** `semgrep` (needs a `pip install semgrep`, and the CI step is
`continue-on-error`); gitleaks; and the full `bench run-tests --app alvoraa_portal`
suite. The full app suite would be several hours in this container — 84 tests took
19 minutes under a Windows bind mount — and the brief named the suites that own
this surface, which is what I ran, plus the four more that cover `auth.py`.

## The bypass count

Counted with the same AST method `test_portal_security_010` uses (docstrings
blanked, tree unparsed, so comments and prose do not count):

| File | Count | Ceiling |
|---|---|---|
| `auth.py` | **0** | 0, newly pinned by this change |
| `joiner_invite.py` | **3** | 3, unchanged |

**No `ignore_permissions` added anywhere.**
