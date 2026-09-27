# 031 - Change a tenant's logo after it is created

Branch `slice/031-console-edit-logo`, from local dev `5ae87c5` (029 is in).
Approved by the user on 2026-09-19 for the first client's go-live in early October.
Local only. No push, no server, no dev tenant.

## The gap

Slice 029 gave `update_tenant` an optional `logo_url` and made it copy the file
to the tenant site. Nothing calls it. The console's Edit Tenant modal has no
logo field, so a customer who rebrands still needs a developer.

This slice is the client half: a logo control in the edit modal that shows what
is there now, uploads a replacement, or removes one.

## What I read first

- `docs/slices/029-tenant-logo-copy/00-fix-notes.md` and the code it describes
- `alvoraa_portal/alvoraa_portal/tenant_api.py` - `_stage_tenant_logo`,
  `update_tenant`, `_run_provision`, `_require_admin`, `_bench_run`
- `alvoraa_portal/alvoraa_portal/www/alvoraa-admin.html` - the create form's
  logo drop zone, `uploadLogoFile()`, `openEditModal()`, `submitEditTenant()`
- `deploy/nginx.conf` - the real `/files/` block, not an assumption
- Frappe v16.33.1 source, read from the bench image in a throwaway
  `docker run --rm --network none` container (no bench touched)

## Functional impact

### Cross-module

| Area | Reach |
|---|---|
| `alvoraa_portal/tenant_api.py` | `update_tenant` (the only endpoint), `_stage_tenant_logo` (shared with create) |
| `alvoraa_portal/auth.py:100` | reads `tenant_logo_url` into the login page's branding |
| `alvoraa_portal/tenant_context.py:33` | same value, with a default |
| `alvoraa-admin.html:1134` | the console tenant list renders `t.logo_url` against the CONTROL PLANE |
| `hrms`, `erpnext`, `alvoraa_goals`, `alvox_compensation` | none. No DocType, no field, no hook, no patch |

Callers of every function I change (`git grep`):

- `update_tenant` - one caller, `alvoraa-admin.html:2055`. No Python caller.
- `_stage_tenant_logo` - two callers, both inside `tenant_api.py`
  (`_run_provision:937`, `update_tenant:597`), plus the 029 tests.
- No signature is removed or reordered; the new parameter is keyword with a
  default, so every existing call keeps working.

### Persona impact

| Persona | Before | After |
|---|---|---|
| Operator (control-plane System Manager) | Could set a logo only at creation | Can change or remove it any time from Edit Tenant |
| CXO / HR Manager on a tenant | Sees the logo the operator set, for ever | Sees the new one after their next page load. **Cannot change it** - see permissions |
| Employee | Same as above | Same |

### HRMS domain impact

None. Leaves, attendance, payroll, appraisals and org structure are untouched.
A logo lives in `site_config.json`, not in the database.

## Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | One extra `os.path.isfile` and one file copy, only when a logo is actually sent. The upload is one POST the create form already makes. |
| Security | improves | Two hardenings while this path becomes reachable from the UI for the first time: an extension allow-list, and a strict shape check on absolute URLs before the value reaches a `shell=True` bench command (see Risks). |
| Reliability | improves | Removal writes an empty value, never a path to a file that is not there. A missing upload still warns instead of storing a broken image. Re-running the same save is safe. |
| Scalability | neutral | Once per tenant edit, not per request. |
| Maintainability | improves | No new endpoint, no second upload path - the edit modal reuses `uploadLogoFile()`. One helper still owns the copy rule. |
| Data integrity | improves | `tenant_logo_url` is written only when the file is on the tenant, or cleared outright. Never a half state. |
| Compliance / privacy | neutral | A company logo is not personal data. The warning line names a file, never a person. No new field appears in any list, export or notification. |
| Accessibility | improves | The new control has a real label, is reachable by keyboard, and its state is stated in words ("No logo set"), not only by a picture. |

## Permissions - the answer

`update_tenant` calls `_require_admin()` first, which needs **both**:

1. `frappe.conf.get("alvoraa_control_plane")` on the site serving the request.
   A tenant site never carries that flag, so on `ppj.localhost` or
   `allabouthr.dev.alvoraa.co` this endpoint does not exist at all - it throws
   `PermissionError` before looking at the user.
2. `System Manager` in the caller's roles on the control-plane site.

So an HR Manager on a tenant cannot change any tenant's logo - not their own,
not anyone else's - on two independent counts. It is already enforced; nothing
to build. A pin test proves both halves so a future edit cannot quietly drop
one.

`upload_file` is Frappe's own endpoint and refuses Guest. The console page
itself is behind the control plane.

## What changing a logo means after the fact

**The old file.** Replacing or removing leaves the previous file on both the
control plane and the tenant. **I chose to leave it.** Deleting is the riskier
choice: one control-plane upload can be referenced by a Frappe `File` record
and, in principle, by more than one tenant, so a delete could break a logo
somewhere else. A stray image file is a few hundred kilobytes, is not personal
data, and nothing links to it once the config is rewritten. Worth saying out
loud rather than leaving unsaid; if the user wants a cleanup it belongs in its
own slice with a reference count.

**Caching - checked, not assumed.** `deploy/nginx.conf` proxies `/files/`
straight to Frappe with no `expires` and no `add_header`; only `/assets/` gets
`expires 30d`. Frappe v16.33.1 serves `/files/` through
`StaticDataMiddleware(SharedDataMiddleware)` in `frappe/middlewares.py`, whose
werkzeug defaults are `cache=True, cache_timeout=43200` - **`Cache-Control:
max-age=43200, public`, twelve hours.**

That would be a problem if the replacement kept the same URL. It does not.
Frappe's `generate_file_name` (`frappe/core/doctype/file/utils.py:192`) checks
whether the path already exists and, if it does, appends the content hash, so a
second upload of `logo.png` is stored as `logoAB12CD.png`. A new file means a
new URL, and no browser has it cached. **No cache-busting parameter or header
change is needed**, which also keeps this slice out of `deploy/nginx.conf` -
not a feature slice's file.

One rare leftover: if the control-plane copy of `logo.png` were deleted and a
different `logo.png` uploaded, the URL would repeat and a browser could show
the old picture for up to twelve hours. A hard reload fixes it. I am recording
it rather than adding machinery for it.

**A half-updated page.** There is none to prevent. `tenant_logo_url` is read
once per page render (`auth.py`, `tenant_context.py`); a page already open keeps
the picture it loaded and picks up the new one on its next load. The write
itself is one `bench set-config` - one file, one value - and `update_tenant`
already ends with `clear-cache` on the tenant site. What I must not do is write
the config before the file is on the tenant, and the 029 helper already
guarantees that order. A test pins it.

## Plan

1. `tenant_api.py` - `update_tenant` gains `remove_logo=0`.
   - `logo_url` untouched and `remove_logo` false - **nothing happens**, exactly
     as today. 029's `test_no_logo_argument_changes_nothing` still pins it.
   - `logo_url` given - unchanged 029 behaviour.
   - `remove_logo` true - `set-config tenant_logo_url ""`. An **empty value**,
     not a path to nothing. `auth.py` then sends `logo_url: ""` and the login
     page falls back.
   - Both given - a plain error: "Choose one: upload a new logo, or remove the
     one that is there."
   - I use a separate parameter rather than a magic `logo_url` value so that
     "" keeps meaning "leave it alone". Overloading "" would break 029's pinned
     no-op.
2. `tenant_api.py` - `_stage_tenant_logo` gains two checks, both refuse-and-warn,
   neither changing what it accepts today:
   - the file extension must be one the create form already offers
     (png, jpg, jpeg, svg, webp, gif);
   - an absolute URL must be a plain `https?://` URL with no quotes, spaces,
     backticks, dollar signs or semicolons. **Why:** `_bench_run` runs
     `subprocess.run(..., shell=True)` and the value is interpolated into the
     command string. Only a control-plane System Manager can reach it, and that
     account can already run bench commands, so this is not a privilege
     escalation - but I am about to make the path reachable from a form, and an
     unquoted value in a shell string should not stay that way. Flagged for the
     user in the report.
3. `alvoraa-admin.html` - a "Company Logo" field in the Edit Tenant modal:
   current logo thumbnail or the words "No logo set", "Upload a replacement",
   and "Remove logo". Reuses `uploadLogoFile()`. Own `ke*` name prefix, its own
   block, nothing existing moved or renamed.
4. New `alvoraa_portal/alvoraa_portal/tests/test_console_edit_logo_031.py` -
   plain unittest, `_bench_run` mocked, no database, following
   `test_tenant_logo_029.py`.

## Limits on screen, and where they come from

| Limit | Value | Source |
|---|---|---|
| Size | 2 MB | What the create form already enforces (`handleLogoFile`). Kept the same so the two forms do not disagree. Frappe's own server limit is System Settings `max_file_size`, default 25 MB (`frappe/core/api/file.py:85`) - far looser, so ours is the one that bites. |
| Type | PNG, JPG, JPEG, SVG, WEBP, GIF | The `accept` list the create form already offers. Now checked in JS by extension and MIME type rather than trusted to `accept`, and checked again server side by extension. |

Messages: "That file is too large - logos must be under 2 MB.", "That is not an
image we can use. Upload a PNG, JPG, SVG, WEBP or GIF." No tracebacks.

## Parallel-work check

`git fetch origin` at the start: **nothing came in.** Local `dev` is one commit
ahead of `origin/dev` (029's `5ae87c5`, not pushed). No incoming diff to read.

| File I will change | Hot file? | Who else is in it |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/tenant_api.py` | yes (shared API file rule) | 029 is finished and merged into local dev. No open row on the work board claims it. |
| `alvoraa_portal/alvoraa_portal/www/alvoraa-admin.html` | not listed, but heavily edited | No open row claims it. 030 is in `access.py` / `attendance_analytics.py` / `performance_api.py`; 013 is the mobile app. |
| `alvoraa_portal/alvoraa_portal/tests/test_console_edit_logo_031.py` | new file | nobody |
| `docs/slices/031-console-edit-logo/` | new | nobody |

**Plan: split.** I add to `tenant_api.py` rather than change any existing
signature, and the console change is one new block in the edit modal plus four
lines in `submitEditTenant`. Nothing is moved, re-indented or renamed.

**Other sessions' uncommitted work in the main checkout** (not mine, not
touched): `.claude/context/ux-learnings.md`, `backlog/KPI_AUTOMATION_BACKLOG.md`,
`docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`,
`hrms/.../alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and
several untracked files. I work in my own worktree, so none of it is at risk.

**Slice 025** owns `alvoraa_portal/public/images/`, the brand helper and the
repair patch. I do not touch any of them. My "remove" writes an empty value,
which is precisely the input 025's fallback chain expects.

**The bench** is claimed by another session for 030, and a third session is on
013. I run nothing on `hrlocal-bench`. Tests are plain unittest with
`_bench_run` mocked - no database, no site - run in a throwaway
`docker run --rm --network none` container, the shape 029 used.

### Tests that pin each behaviour

| Behaviour | Test |
|---|---|
| Update with a logo copies it, then writes the path | `test_a_new_logo_is_copied_before_the_config_is_written` |
| Update with no logo changes nothing | `test_an_edit_that_does_not_mention_the_logo_leaves_it_alone` |
| Remove writes an empty value, not a path | `test_remove_writes_an_empty_value` |
| A rejected type | `test_a_file_type_we_do_not_serve_is_refused` |
| Permission boundary | `test_a_tenant_site_has_no_tenant_management_at_all`, `test_an_hr_manager_cannot_change_a_logo` |
| The console really calls it | `test_the_edit_modal_sends_the_logo_to_update_tenant` (static check of the page) |

## Risks

1. **`shell=True` in `_bench_run`.** Pre-existing, twenty call sites, reachable
   only by a control-plane System Manager. I am narrowing the one value this
   slice makes form-reachable, not rewriting `_bench_run`. A proper fix (an
   argument list instead of a command string) is its own slice.
2. **SVG logos.** The create form already accepts SVG, and an SVG opened
   directly at `/files/x.svg` on a tenant runs its own script, same origin. As an
   `<img src>` it cannot. I am not changing the accepted types in this slice -
   that is a product decision - but it is on the record.
3. **A tenant whose stored logo is already broken** is slice 025's repair, not
   mine. The edit control shows "No logo set" when the value is empty; when the
   value points at a missing file the thumbnail would break, so the modal has an
   `onerror` fallback that says "The saved logo could not be loaded" instead -
   client-side only, touching nothing 025 owns.

---

## Addendum, 2026-09-19, after the build

Risk 2 above - "SVG logos stay accepted, that is a product decision" - **was
decided by the user the same day: drop SVG, and GIF with it. A logo is a PNG, a
JPG/JPEG or a WEBP.**

So the "Limits on screen" table above is out of date from the moment of that
decision: read `03-implementation-notes.md` for what was actually built. The
list is narrower in three places at once - the server's `_LOGO_EXTENSIONS`
(the real guard), both forms' `accept` attributes, and the one shared
JavaScript check - and the message now says what to do next rather than only
what went wrong.

Risk 1, `shell=True` in `_bench_run`, has been taken as **slice 032** by the
session that owns `tenant_api.py`. The absolute-URL narrowing built here stays
as the interim guard until 032 lands; it must not be removed before then.
