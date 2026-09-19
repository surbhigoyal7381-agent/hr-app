# 031 - Change a tenant's logo after it is created: what was built

Branch `slice/031-console-edit-logo`, from local dev `5ae87c5`.
Local only. Not merged into local `dev`, not pushed, no server touched.
Read `00-impact-analysis.md` first.

## What the control looks like

In the console's **Edit Tenant** dialog, under Support Email, a "Company Logo"
field:

- **A tenant with a logo** shows the picture, the words "Current logo" and
  "Shown on this tenant's login page.", and two buttons: *Upload a replacement*
  and *Remove logo*.
- **A tenant with no logo** says so in words - "No logo set" / "The login page
  shows the Alvoraa mark instead." - and the button reads *Upload a logo*.
  There is no broken picture and no empty grey box.
- **A tenant whose stored logo points at a file that is not there** says "The
  saved logo could not be loaded - Upload it again, or remove it so the Alvoraa
  mark is used." That is an `onerror` fallback in the dialog only; slice 025
  still owns the real repair.
- **After choosing a file**: the preview changes, the line reads
  "New logo ready - <file name> - saved when you click Save Changes", and an
  *Undo* button appears.
- **After clicking Remove logo**: "The logo will be removed - Saved when you
  click Save Changes. The login page will show the Alvoraa mark." *Undo* again.

Nothing is sent until **Save Changes**. Undo puts the dialog back to the
tenant's real state, so a misclick costs nothing.

## What each action writes

| The operator does | What the console sends | What the server writes |
|---|---|---|
| Edits a name, a colour, a module | no logo argument at all | nothing about the logo |
| Uploads a replacement | `logo_url: "/files/<name>"` after a POST to `upload_file` | the file is copied to the tenant first, then `tenant_logo_url` is set to the same relative path |
| Removes the logo | `remove_logo: 1` | `tenant_logo_url` is set to an **empty value** (`set-config tenant_logo_url ""`) |
| Both at once | not possible from the dialog | refused with "Choose one: upload a new logo, or remove the one that is there." |
| Uploads something that is not a picture | refused in the browser before the upload | and refused again on the server, with "[WARN] Logo not applied: that is not an image we can show." |

"Remove" writes an empty value, never a path to a file that is not there.
`auth.py` then hands the login page `logo_url: ""`, which is exactly the input
slice 025's fallback chain expects.

## File by file

| File | Change | Mechanism, and why |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/tenant_api.py` | `update_tenant` gains `remove_logo=0`; `_stage_tenant_logo` gains an extension allow-list and a shape check on absolute URLs; new `_as_flag` helper | **Extend.** No new endpoint - the brief said so and it is right: one door, one guard. A separate `remove_logo` argument rather than a magic `logo_url` value, so `""` keeps meaning "leave it alone" and 029's pinned no-op survives untouched. |
| `alvoraa_portal/alvoraa_portal/www/alvoraa-admin.html` | one new block in the Edit Tenant modal, one new JS section (`keLogo*`), four lines inside `submitEditTenant` | **Extend.** Reuses the existing `uploadLogoFile()`, so there is still exactly one call to `/api/method/upload_file` in the page - a test pins that. Own `ke-` / `ke` name prefix, its own block; nothing existing moved, re-indented or renamed. |
| `alvoraa_portal/alvoraa_portal/tests/test_console_edit_logo_031.py` | new, 21 tests | **Build.** Plain unittest, `_bench_run` mocked, no database. |
| `alvoraa_portal/alvoraa_portal/tests/test_tenant_logo_029.py` | one docstring | 029's docstring said "the console's edit modal sends no logo today". It does now. The assertion is unchanged; only the sentence explaining it. |
| `docs/slices/031-console-edit-logo/` | new | these notes and the impact analysis |

No DocType, no field, no hook, no patch, no migration. Nothing in
`alvoraa_portal/public/images/`, the brand helper or the repair patch - slice
025 owns those and they were not touched.

## The acceptance list

| Asked for | How it is met |
|---|---|
| An edit-logo control that shows the current logo | `ke-logo-img` plus `ke-logo-state`, filled from `t.logo_url` when the dialog opens |
| ...or plainly says there is none | "No logo set" in words, not an empty box |
| ...lets you upload a replacement | `keChooseLogo` then `uploadLogoFile` on save |
| ...lets you remove one | `keRemoveLogo` then `remove_logo: 1` |
| State what "remove" writes | an empty value - `set-config tenant_logo_url ""`. Pinned by `test_remove_writes_an_empty_value`, which also asserts the command holds no path, no "None" and no "null" |
| Wire to `update_tenant`'s `logo_url`, no new endpoint | done; the only endpoint the dialog calls is still `update_tenant` |
| Keep the no-op when the field is untouched | `test_an_edit_that_does_not_mention_the_logo_leaves_it_alone`, and 029's own no-op test still passes |
| The old file | left in place, deliberately - see below |
| Caching | checked against `deploy/nginx.conf` and the Frappe source; no change needed - see below |
| No half-updated page | nothing to fix; the write is one config value and the file is always copied first. `test_a_new_logo_is_copied_before_the_config_is_written` proves the order |
| Permissions | already enforced; three tests now pin it |
| Plain English and actionable errors | listed above; limits below |

Nothing on the list was left unmet.

## The three questions in the brief

**The old file.** Replacing or removing leaves the previous file on both the
control plane and the tenant, on purpose. Deleting is the riskier choice: a
control-plane upload is also a Frappe `File` record and could in principle be
referenced by another tenant, so a delete could break a logo somewhere else. A
stray image is a few hundred kilobytes, is not personal data, and nothing links
to it once the config is rewritten. `test_removal_does_not_delete_the_file`
records the decision so a later change has to argue with a test rather than
with a comment. If the user wants a cleanup it needs a reference count, and
that is its own slice.

**Caching - checked, not assumed.** `deploy/nginx.conf` proxies `/files/`
straight to Frappe with no `expires` and no `add_header` (only `/assets/` gets
`expires 30d`). Frappe v16.33.1 serves `/files/` through
`StaticDataMiddleware(SharedDataMiddleware)`, whose werkzeug defaults are
`cache=True, cache_timeout=43200` - so a logo comes back with
`Cache-Control: max-age=43200, public`: **twelve hours**.

That would matter if a replacement kept the same URL. It does not. Frappe's
`generate_file_name` appends the content hash when the path already exists, so
a second upload of `logo.png` is stored as `logoAB12CD.png`. A new name means a
new URL and no browser has it cached. **No cache-busting name or header was
needed**, and `deploy/nginx.conf` was not touched.

One rare leftover, recorded rather than engineered around: if the control-plane
copy of `logo.png` were deleted and a different `logo.png` uploaded, the URL
would repeat and a browser could hold the old picture for up to twelve hours. A
hard reload fixes it.

**A half-updated page.** There is none to prevent. `tenant_logo_url` is read
once per page render (`auth.py:100`, `tenant_context.py:33`). A portal page
already open keeps the picture it loaded and picks up the new one on its next
load - it never shows half of each. The dangerous order would be writing the
config before the file reaches the tenant; 029's helper prevents that and
`test_a_new_logo_is_copied_before_the_config_is_written` now proves it by
checking the file is on disk at the moment the `set-config` runs. The write
itself is one value in one file, and `update_tenant` already ends with
`clear-cache` on the tenant site.

## Permissions - the answer

`update_tenant` calls `_require_admin()` before anything else, and that needs
**both**:

1. `alvoraa_control_plane` in the serving site's `site_config.json`. A tenant
   site never carries it, so on a tenant the endpoint does not exist - it
   raises `PermissionError` before it even looks at the user.
2. `System Manager` in the caller's roles on the control-plane site.

**An ordinary tenant user, including an HR Manager, cannot change any tenant's
logo - their own or anyone else's.** It was already enforced; nothing had to be
built. Three tests now pin it with the real guard (not mocked):
`test_a_tenant_site_has_no_tenant_management_at_all`,
`test_an_hr_manager_cannot_change_a_logo`, `test_guest_cannot_change_a_logo`.
Each asserts `PermissionError` **and** that `_bench_run` was never called, so a
future refactor cannot let the work happen before the guard.

## Limits on screen, and where they come from

| Limit | Value | Source |
|---|---|---|
| Size | 2 MB | the same limit the create form already enforces in `handleLogoFile`. Frappe's own server limit is System Settings `max_file_size`, default 25 MB (`frappe/core/api/file.py:85`) - far looser, so ours is the one that bites |
| Type | PNG, JPG, JPEG, SVG, WEBP, GIF | the list the create form's `accept` already offers. Now checked by extension **and** MIME prefix in the browser rather than trusted to `accept`, and by extension again on the server |

On screen: "That file is too large - logos must be under 2 MB." and "That is
not an image we can use. Upload a PNG, JPG, SVG, WEBP or GIF." The hint under
the field reads "PNG, JPG, SVG, WEBP or GIF, under 2 MB. Nothing changes until
you click Save Changes." No tracebacks anywhere; if the server returns a
`[WARN]` line, the dialog shows it as a plain sentence and stays open.

## The seven dimensions, against the code actually written

| Dimension | Before → after | One line |
|---|---|---|
| Performance | neutral | One `os.path.isfile` and one file copy per save, and only when a logo was actually chosen. Removal is one `set-config`. No new query, no new request on any tenant page. |
| Security | **improves** | Two real hardenings on a path this slice makes form-reachable: a file-extension allow-list, and a shape check that keeps quotes, spaces, backticks, `$`, `;`, `&` and newlines out of a value that ends up in a `shell=True` command. Six crafted URLs are pinned as refused. The permission guard is now proved rather than assumed. |
| Reliability | **improves** | Removal writes an empty value, never a dangling path. The dialog never sends both actions. `_as_flag` fails closed, so an unrecognised `remove_logo` does nothing rather than deleting a logo. Saving the same thing twice is safe. |
| Scalability | neutral | Once per tenant edit, by one operator. Nothing per-request, per-employee or per-month. |
| Maintainability | **improves** | No second endpoint and no second upload path - a test asserts there is still exactly one call to `upload_file` in the page. One helper still owns the copy rule for both create and update. |
| Data integrity | **improves** | `tenant_logo_url` is either a path to a file that is on the tenant, or empty. There is no third state, and the order is now pinned by a test. |
| Compliance / privacy | neutral | A company logo is not personal data. No new field reaches any list view, export, notification or log line. The warning names a file, never a person. Visibility was not widened anywhere - the dialog shows the operator only the logo of the tenant they already opened. |

Plus, because the brief asked for it: **accessibility improves.** The control
has a real `<label for="edit-logo">`, every action is a `<button>` reachable by
keyboard with the console's visible focus ring, the state is stated in words as
well as shown as a picture, and the error text says what to do next.

Personas: **Operator** gains the whole feature. **CXO / HR Manager / Employee**
on a tenant see the new logo on their next page load and still cannot change it.

## NFR notes

- **Query count:** zero. Nothing in this slice reads or writes the database.
- **Indexes:** none needed.
- **Background jobs:** none added. The existing module-install job is untouched.
- **Permission enforcement points:** `_require_admin()` at the top of
  `update_tenant`; Frappe's own guard on `upload_file`. Both server side.
- **Sensitive fields touched:** none.
- **Fallbacks:** a logo that cannot be applied leaves the old value in place
  and reports why; an empty value falls back to the Alvoraa mark.

## What else moved while I worked

`git fetch origin` at the start and again before finishing: **nothing came in.**
`git log dev..origin/dev` was empty both times. Local `dev` is one commit ahead
of `origin/dev` (029's `5ae87c5`, not pushed). No incoming diff to read, no
conflict to resolve, nothing of anyone else's to prove survived.

Other sessions' uncommitted work in the main checkout (`ux-learnings.md`,
`KPI_AUTOMATION_BACKLOG.md`, `009-.../00-assessment-and-plan.md`,
`alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, several
untracked files) is untouched - all work was done in this worktree.

The bench was **not** touched: slice 030 holds it and 013 is also running.

## Commands run, and what they said

All test runs were in a throwaway `docker run --rm --network none` container
from the bench image `ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3`, with
this worktree mounted **read-only**. `hrlocal-bench` was never used, no
`docker cp`, no site, no database.

| Command | Result |
|---|---|
| `env/bin/python -m unittest alvoraa_portal.tests.test_console_edit_logo_031` | **21 tests, OK** (0.18 s) |
| the same, plus `...test_tenant_logo_029` | **37 tests, OK** (0.16 s) - 029 still passes unchanged |
| the 031 tests against `tenant_api.py` and `alvoraa-admin.html` from `5ae87c5` | **16 of 21 fail** (7 failures, 9 errors) - see below |
| `python scripts/check_app_integrity.py` | 593 checks, "OK - all consistent" |
| `node scripts/check_portal_handlers.js alvoraa-admin.html` | "all reachable and callable" |
| `node scripts/check_undefined_js.js alvoraa-admin.html` | "undefined identifiers: none" |
| `python scripts/check_design_system.py` | "OK - the visual system holds"; `alvoraa-admin.html` scores 0 on every column |
| `python -m py_compile` on both changed Python files | clean |
| `python -m ruff check` on both | 5 findings in `tenant_api.py`, **all on pre-existing lines** (unused imports at 14, 1421, 1437, 1458, 1664) - the same five 029 reported. The test file is clean. |

### Fail-without-fix

Against the code as it was at `5ae87c5`, 16 of the 21 new tests fail:

- **9 errors** - `remove_logo` does not exist, so every removal test and the
  three permission tests die on `TypeError: update_tenant() got an unexpected
  keyword argument`.
- **7 failures** - the console page has no logo control at all (5 tests), a
  `.pdf` or `.exe` "logo" is accepted and written (1), and an absolute URL
  carrying `"; touch /tmp/pwned; echo "` is written straight into the shell
  command (1).

The 5 that pass without the fix are the ones that exist to **pin behaviour that
was already right**, not to prove new work: the copy-before-config order, the
untouched-edit no-op, the accepted file types, a plain absolute URL, and "only
one upload path in the page". That is what they are for - a bad merge that
drops any of them fails CI.

Honest note on the three permission tests: without the fix they error on the
missing argument rather than on a missing guard, so their value is as **pins**,
not as a fail-without-fix proof. The guard itself is pre-existing and correct;
what the tests add is that it can no longer be quietly removed.

## Known gaps and shortcuts

1. **The full `alvoraa_portal` suite was not run.** It needs a site and the
   bench, which another session holds for slice 030. What I ran instead: both
   logo modules, plus the three static page checks and the integrity check.
   `bench run-tests --app alvoraa_portal --module
   alvoraa_portal.tests.test_console_edit_logo_031` is worth one short bench
   window for the record, though nothing in it reads a database.
2. **The UI was traced by hand, not clicked in a browser** - the bench is not
   mine to start. `check_portal_handlers.js` calls every new handler in a
   stubbed DOM and `check_undefined_js.js` finds no undefined identifier, which
   is the shape of failure this page has actually shipped before. A real click
   through Edit Tenant on the local bench is still owed before this goes to dev.
3. **`_bench_run` still runs `shell=True` with a built command string.** I
   narrowed the one value this slice makes form-reachable; I did not rewrite
   `_bench_run`. Twenty call sites, reachable only by a control-plane System
   Manager who can already run bench commands - so not an escalation, but it
   should become an argument list in a slice of its own. **This is the thing I
   would fix next.**
4. **SVG logos stay accepted**, as the create form already accepts them. An SVG
   opened directly at `/files/x.svg` on a tenant runs its own script on the
   tenant's origin; as an `<img src>` it cannot. Removing SVG is a product
   decision, so it is on the record rather than done quietly.
5. **Old logo files accumulate.** Decided, not forgotten - see above.
6. **No `Cache-Control` change**, because the evidence said none was needed.
   The one rare stale case is written down above.
