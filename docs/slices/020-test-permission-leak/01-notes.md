# Slice 020 — the test suites that took permissions and never gave them back

Test-only fix. No product code changed.

## The problem, in one paragraph

A `Custom DocPerm` row does not add to a doctype's permissions — it **replaces**
them. Frappe checks per doctype (`frappe/permissions.py`, v16.33.1): if any
custom row exists for a doctype, the shipped rows are ignored completely. Our
`module_access.sync_permissions()` uses that on purpose, to deny a module the
tenant did not buy, and it **commits** the rows. A test's rollback cannot undo a
commit. Only `module_access.release_permissions()` can, and it does it properly:
it deletes only the doctypes we recorded, puts snapshotted rows back verbatim,
and calls `frappe.clear_cache()`.

One suite denied ~450 doctypes and never released them. Unrelated suites that
ran afterwards then died in `setUpClass` with permission errors on doctypes they
had never heard of. Measured on the shared local `test_site`: **554 leftover rows
across 338 doctypes.**

## Which suites leaked

I walked the whole test tree with an AST scan, not a grep, and found **ten**
classes that call `sync_site()` or `sync_permissions()`. Two had no restore:

| Suite / class | How it leaked |
|---|---|
| `test_module_access.py::TestHrKeepsTheDesk` | `setUp` called `ma.sync_site(starter)` — a full deny of every doctype outside the plan, committed. `tearDown` only called `frappe.db.rollback()`. **This is the whole 554 rows.** 6 tests, so the deny ran 6 times per run. |
| `test_module_access.py::TestTenantAdminExemption` | `test_the_control_plane_is_never_gated` calls `ma.sync_site()` with `alvoraa_control_plane = 1`. It writes nothing **today**, only because the guard returns early. If that guard ever broke, this test would silently poison the site instead of failing. |

Two more restored correctly but through `tearDown` alone, which is a hole:
**unittest does not run `tearDown` when `setUp` raises**, and in both cases the
deny happens in `setUp` with code after it that can raise.

| Suite | The hole |
|---|---|
| `test_tenant_setup.py::TestDefaultUsers` | `sync_site(business)` in `setUp`, then a `delete_doc` loop that can raise. Its `tearDown` comment already describes this exact bug — it was fixed once, but only for the happy path. |
| `test_access_control.py::Wave4Mixin` | Restores in `setUp` and `tearDown`, but the user insert between them can raise. |

Nothing outside `alvoraa_portal` writes these rows. `hrms`, `alvoraa_goals` and
the `grace_*` apps have no caller. The two 010d tests that do insert a row
(`test_review_copies_010d`, `test_review_outside_010d`) use `db_insert` with
`frappe.db.rollback()` in a `finally` and never commit, so they are clean.

## What I changed — test files only

1. `test_module_access.py` — `self.addCleanup(ma.release_permissions)` in
   `TestHrKeepsTheDesk.setUp`, registered **before** the `sync_site` call, and
   the same on the control-plane test.
2. `test_tenant_setup.py` — the same cleanup, registered before the write. The
   existing `tearDown` release stays; releasing twice is a proven no-op
   (`test_releasing_twice_is_harmless`).
3. `test_access_control.py` — the same cleanup in `Wave4Mixin.setUp`.
4. New `test_permission_leak_020.py` — the guard, below.

`addCleanup` rather than `tearDownClass` on purpose: a cleanup registered before
the write runs even when `setUp` raises afterwards, and it runs on failure.

No blanket `frappe.db.delete("Custom DocPerm")` anywhere. A tenant's honest
baseline is **not** zero — `hrms/setup.py` writes rows at install via
`add_permission` and `update_permission_property` — so a sweep would throw a real
customer's permission configuration away along with the leak. The invariant is
"the count does not change", not "the count is zero".

## The guard

`test_permission_leak_020.py`, two layers:

* **Static (the real guard).** Parses every `test_*.py` in the suite with `ast`
  and fails if a class calls `sync_site`/`sync_permissions` without
  `release_permissions` on itself or on a base class in the same file. Order
  cannot hide anything from it, and it fails on the file being written rather
  than on a victim three suites later. It carries its own fail-first proof: a
  planted leaky class, a class that restores via `addCleanup` on a base, and a
  class that only quotes the name in a string.
  - `ast`, not grep, because `test_provision_guards` and `test_module_access`
    both pass these names to `inspect.getsource`. A grep version flagged both as
    offenders — a false failure on two innocent files.
  - Deniers count only when **called**; restores count when merely
    **mentioned**, because `addCleanup(ma.release_permissions)` is a reference.
* **Runtime (a tripwire, not proof).** Asserts nothing is recorded as restricted
  when this file runs, and that a narrow deny/release round trip returns the row
  count *and* the distinct-doctype count to where they started. Frappe runs a
  module's files in name order, so this file sits after the two leaking suites
  and just before `test_portal_security_010`, the suite that was breaking. It
  cannot see a file that sorts after it, and that order is not a promise Frappe
  makes — which is why it is the second guard, not the first.

Scope limit, stated plainly: the static scan reads
`alvoraa_portal/alvoraa_portal/tests` only. That is where every caller lives
today. A caller added under another app's test folder would not be seen.

## Slice 010's workaround stays

`test_portal_security_010.py::_Base.setUpClass` calls
`module_access.release_permissions()` to work around this. It is now
unnecessary, and it is **left in place** on purpose: it is harmless, other
sessions rely on it, and it is a cheap second net if a new leak ever appears.

## Still open — not fixed here

`Module Profile` leaks the same way and is a different doctype.
`test_subscription_access.py::TestAppliedToThisSite` and
`TestGatingReadsTheSiteConfig` rebuild the site's `Module Profile` through
`sync_module_profile` and restore `Workspace.is_hidden` and their users, but not
the profile itself. It has not broken a suite, so it is reported rather than
changed.
