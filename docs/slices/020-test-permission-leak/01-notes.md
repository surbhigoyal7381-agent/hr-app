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

## The bigger finding: a product bug, not only a test bug

**The test fix alone does not close the leak.** While proving the fix I found why
a delete-and-clear repair kept coming undone, and why slice 010's
`release_permissions()` workaround did not help either.

`sync_permissions()` writes the denial rows first and records what it did
**last**:

```
frappe.db.delete("Custom DocPerm", {"parent": dt})   # line 505
_keep_exempt_row(dt, exempt)                         # line 508 - the row is written
...
if restricted:
    _save(restricted=..., snapshot=snapshot)         # line 516 - the record
frappe.db.commit()                                   # line 518 - never reached on error
```

`_save()` raises `TimestampMismatchError` on this bench. It is in the Error Log
on `test_site` three times in four minutes on 2026-09-18, each swallowed by
`sync_site`'s try/except:

```
module_access.py line 516, in sync_permissions -> _save(...)
module_access.py line 313, in _save -> doc.save(ignore_permissions=True)
frappe.exceptions.TimestampMismatchError: Alvoraa Access State has been modified
after you have opened it (13:39:35.133205, 13:39:37.091849)
```

When that happens the rows are already written, the state record says nothing was
restricted, and `sync_site` carries on to `apply_to_users()` — **which commits**.
So the rows are committed and **unrecorded**, and `release_permissions()` cannot
touch them, because by design it only releases what we recorded.

Demonstrated on `test_site`, bounded to three doctypes:

| Step | Rows | Recorded |
|---|---|---|
| start | 0 | 0 |
| `sync_permissions` with `_save` forced to fail | **3** | **0** |
| `release_permissions()` → `{'released': [], 'still_restricted': []}` | **3** | 0 |

That is the "554 rows nobody can put back" state exactly, and it is why 322 rows
were back within an hour of the manual delete.

**This is production code (`alvoraa_portal/module_access.py`) and I did not
change it**, per the brief. Reported for a decision. The shape of the fix looks
like: record the intent before writing the rows, or clear the Single's document
cache before `_save` reloads it, or let the error out of `sync_site` instead of
swallowing it. All three change behaviour other slices depend on.

## A second thing the release pass needs to know

`test_access_control.py::TestReversalFirst::test_it_restores_pre_existing_customisations_exactly`
**fails on `test_site` right now**:

```
AssertionError: [] is not true : this test needs a doctype that has custom perms
```

It is not my change and it is not a product fault. The earlier blanket repair
deleted **every** `Custom DocPerm` row on `test_site`, including the install-time
rows that were legitimately there, so `Salary Slip` now has none and the test's
own precondition cannot hold. For comparison, `ppj.localhost` has 625 rows across
351 doctypes. `test_site` is at **0**. The test will pass again once the site is
rebuilt or reinstalled. This is the cost of the blanket sweep, and the reason the
new guard asserts "the count does not change" rather than "the count is zero".

## What I ran

Bench taken only when `pgrep -af run-tests` was clear, one run at a time, and
released afterwards. The shared bench mounts the **main checkout**, so the fixed
code was run from a throwaway container (`hrlocal-020`) mounting this worktree
against the same `test_site`; the container has been removed.

```
bench --site test_site run-tests --module alvoraa_portal.tests.test_access_control
bench --site test_site run-tests --module alvoraa_portal.tests.test_module_access
bench --site test_site run-tests --module alvoraa_portal.tests.test_tenant_setup
bench --site test_site run-tests --module alvoraa_portal.tests.test_permission_leak_020
bench --site test_site run-tests --module alvoraa_portal.tests.test_portal_security_010
```

| Module | Result | Rows / doctypes after |
|---|---|---|
| — start — | | 0 / 0 |
| `test_access_control` | 34 tests, 1 failure (the pre-existing one above) | 0 / 0 |
| `test_module_access` | 51 tests, OK | 0 / 0 |
| `test_tenant_setup` | 10 tests, OK | 0 / 0 |
| `test_permission_leak_020` | 5 tests, OK (3.2s) | 0 / 0 |
| `test_portal_security_010` (the victim) | 45 OK + 5 OK | 0 / 0 |

The victim module passes where it used to error, and every module leaves the row
count and the doctype count exactly where it found them.

**Honest limit on the fail-first proof.** I ran `test_module_access` against the
**unfixed** main checkout first, and it left 0 rows — so I did not reproduce the
554-row leak today. The reason is the product bug above: on this site
`sync_permissions` currently raises before it commits, and the runner's rollback
took the rows back. The leak is real and was measured twice by other sessions;
what I could prove deterministically is the mechanism (the table above) and that
the fixed suites restore what they change.

## Still open — not fixed here

`Module Profile` leaks the same way and is a different doctype.
`test_subscription_access.py::TestAppliedToThisSite` and
`TestGatingReadsTheSiteConfig` rebuild the site's `Module Profile` through
`sync_module_profile` and restore `Workspace.is_hidden` and their users, but not
the profile itself. It has not broken a suite, so it is reported rather than
changed.
