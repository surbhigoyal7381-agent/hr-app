# 029 - A tenant's uploaded logo never reached the tenant's site

Small approved fix. Branch `slice/029-tenant-logo-copy` from local dev `886c8c4`.

## The bug

The admin console uploads the logo with `upload_file` on the **control plane**
site (the one the console runs on, e.g. `dev.alvoraa.co`). It then hands the
returned relative path (`/files/<name>.png`) to `create_tenant`, which writes it
into the tenant's `site_config.json` as `tenant_logo_url`.

Frappe keeps public files per site (`sites/<site>/public/files/`). The tenant
site never had the file, so every tenant page that shows `cfg.logo_url` showed
a broken image. The console's own tenant list rendered the same path against
the control plane, so it looked fine there - which is why nobody noticed.

Seen on `allabouthr.dev.alvoraa.co`: `logo_url: /files/AllAboutHR1.png`, 404.

## What changed

One file of code, one new test module, this note.

`alvoraa_portal/alvoraa_portal/tenant_api.py`

- New helper `_stage_tenant_logo(site_name, logo_url, control_site=None)`.
  Returns `(url_to_store, warning)`.
  - `http(s)://...` - stored as-is, nothing copied.
  - `/files/<name>` - copied with `shutil.copy2` from
    `sites/<control site>/public/files/<name>` to
    `sites/<tenant>/public/files/<name>`, then stored as the same relative
    path so the tenant stays self-contained. Control site comes from
    `frappe.local.site`.
  - Source missing - nothing is stored, and a `[WARN] Logo not applied ...`
    line is returned for the job log or the API message. Never a broken image.
  - The name must be a bare file name (`^/files/[A-Za-z0-9][A-Za-z0-9._ ()-]*$`,
    no `..`, no directory part). Anything else is refused before a path is
    built, so a crafted value cannot make the copy read outside `public/files`.
- `_run_provision` (the job behind `create_tenant`): calls the helper, appends
  the warning to the job log, writes `tenant_logo_url` only when the helper
  returned a path. A comment there says why the bug went unseen.
- `update_tenant`: gains an optional `logo_url=""` parameter that goes through
  the same helper. The warning is appended to the returned `message`.

`alvoraa_portal/alvoraa_portal/tests/test_tenant_logo_029.py` - 16 tests.

## Something the brief assumed that was not there

The brief said to fix "the two sites that write `tenant_logo_url`" - create
and update. **`update_tenant` never wrote `tenant_logo_url`**: it had no
`logo_url` parameter, and the console's edit modal sends none. So the update
path did not have the bug; it had no logo support at all. I added the optional
parameter (server side only, no console change) so the brief's "update path
behaves the same" test is real and so a later console change cannot
reintroduce the bug. With no `logo_url` the update path is unchanged, and a
test pins that.

## Tests - no database, no site, no bench window needed

The tests are plain `unittest.TestCase`. They point `SITES_DIR` at a temporary
folder, set `frappe.local.site` directly, and replace `_bench_run`,
`subprocess.run`, the jobs file, the credential store and `now_datetime()`
(which reads System Settings) - following `test_provision_guards.py`.

Run in a throwaway `docker run --rm --network none` from the bench image
`ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3` with this worktree mounted
read-only. `hrlocal-bench` was not touched.

- With the fix: **16 tests, OK** (0.06 s).
- Fail-without-fix (same tests against `tenant_api.py` from `886c8c4`):
  **2 failures, 11 errors**. The two create-path tests fail because the old
  code wrote the path with no copy; the rest error because the helper does not
  exist.
- `bench run-tests --app alvoraa_portal --module alvoraa_portal.tests.test_tenant_logo_029`
  will also run them on a site, but nothing in them reads or writes a database.

Static: `python -m py_compile` clean. `ruff check` on both files: 5 findings in
`tenant_api.py`, all on pre-existing lines (14, 1380, 1396, 1602 - unused
imports), identical to the file before the change; the test file is clean.

## NFR check against the code written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One `os.path.isfile` and one file copy per provision or update, only when a relative path is given. |
| Security | improves | The name is validated before any path is built; `..`, absolute paths, hidden files and backslashes are refused. Tested. |
| Reliability | improves | A missing source no longer produces a broken image; it is reported. The copy runs by itself safely twice. |
| Scalability | neutral | Runs once per tenant, not per request. |
| Maintainability | improves | One helper used by both paths, one regex, one message. |
| Data integrity | improves | `tenant_logo_url` is written only when the file exists on the tenant. |
| Compliance / privacy | neutral | A logo is not personal data. The WARN line names the file, not a person. |

Personas: CXO and HR Manager on a tenant now see the logo the operator
uploaded. Employees the same. The operator sees a clear warning in the job log
or the save message when the upload is missing.

## Not done, on purpose

- No repair of tenants already carrying a broken `tenant_logo_url` - slice 025
  owns that with an existence check.
- No change to `alvoraa-admin.html`.
- Not run on `hrlocal-bench`, not merged into local dev, not pushed.

## Owed

Nothing for the database. The tests need no bench. If the user wants the
module run through `bench run-tests` on `test_site` for the record, that is a
short run in a bench window.
