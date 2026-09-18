# The last failing test: it was waiting for the site to be a certain way

Test file only. No product code changed.

## What was wrong

`test_access_control.TestReversalFirst.test_it_restores_pre_existing_customisations_exactly`
read whatever `Salary Slip` happened to carry:

```python
before = self._custom_roles("Salary Slip")
self.assertTrue(before, "this test needs a doctype that has custom perms")
```

On a freshly built `test_site`, `before` is `[]` and the test cannot run.

## The premise is not just unreliable — it is false

The docstring said "40 of the 450 doctypes a Starter tenant blocks already carry
Custom DocPerm rows". I checked it on the rebuilt site rather than trusting it.
Of the **45** doctypes that carry custom permission rows, **none** is in the
Starter-blocked set of **322**:

```
carrying rows AND blocked on starter: 0 []
```

That is not an accident of this site. The install-time rows land on HR and core
doctypes — `Employee`, `Leave Application`, `Attendance`, `Company`, `Role`,
`Currency` — which are exactly the ones a Starter plan **keeps**, plus ERPNext
plumbing that `blocked_doctypes` deliberately exempts. So a doctype that is both
blocked and already customised does not arise from an install at all. It arises
when a **tenant's administrator** customises something their plan does not
include, which is a real situation and the one worth testing.

**So the test was worth keeping, and it was worse than failing: the code path it
guards had no coverage at all.** A doctype with no custom rows takes the other
branch in `sync_permissions` — restored by doing nothing — so on a fresh site
nothing exercised the snapshot-and-restore branch that exists precisely for the
customised case.

I did not change what the test asserts. I made it build the precondition.

## What I changed

`alvoraa_portal/alvoraa_portal/tests/test_access_control.py` only.

1. **`_give_it_a_pre_existing_customisation(doctype)`** in `Wave4Mixin` builds
   the precondition with `frappe.permissions.add_permission` and
   `update_permission_property` — Frappe's own API, and the same two calls
   `hrms/setup.py` uses, so the fixture reproduces the real situation rather
   than imitating it. `add_permission` copies the doctype's standard rows into
   `Custom DocPerm` first, which is how a doctype comes to carry a set of them.
   It asserts up front that the doctype really is Starter-blocked, so the test
   cannot quietly stop proving anything if the plan changes.
2. A dedicated role, `Wave4 Fixture Customisation`, so the customisation is
   recognisably the test's own and cannot collide with a role the site uses.
3. **`_put_the_doctype_back`** restores that one doctype exactly — snapshot its
   rows before touching it, delete, re-insert the originals, drop the role,
   clear the cache. Bounded to one doctype, never a sweep of the table: on a
   real tenant those rows are the configuration. It calls
   `release_permissions()` **first**, so it does not depend on cleanup order
   (cleanups run last-registered-first, and the mixin's release would otherwise
   run after this one and restore its snapshot on top).
4. **`_custom_perms(doctype)`** compares every field of every row, not just the
   role names. `_custom_roles` cannot see a changed flag, and "restores the
   customisation **exactly**" is a claim about the flags. This is a stronger
   assertion than the one it replaces.
5. Two guards against the test passing for the wrong reason:
   - `assertNotEqual` after the sync — the doctype really was denied, so the
     restore is undoing something.
   - `assertIn(dt, ma._load("permission_snapshot"))` — the **snapshot branch**
     is the one that ran. This is the assertion that makes the test about
     snapshots rather than about nothing.

## Results

Bench taken only when `pgrep -af run-tests` was clear, one run at a time,
released afterwards. The shared bench mounts the main checkout, so the fixed
code ran from a throwaway container (`hrlocal-022`) mounting this worktree
against the same `test_site`; the container has been removed.

| Run | Result | Custom DocPerm after |
|---|---|---|
| — start — | | **228 rows / 45 doctypes** |
| `test_access_control` | **34 tests, OK** (was 1 failure) | 228 / 45 |
| `test_permission_leak_020` | 5 tests, OK | 228 / 45 |
| full `alvoraa_portal` | **1,242 tests (584 + 658), OK — no failures, no errors** | 228 / 45 |
| full `alvoraa_goals` | **18 tests, OK (skipped=2)** | 228 / 45 |

The count never moved off **228 / 45**. Afterwards: `0` recorded restrictions,
and `0` rows in `tabRole` matching the fixture role — the fixture cleans up
after itself.

## One honest limit

The fail-first evidence is that the old test failed on this site (reproduced,
and the reason diagnosed above) and that the new one passes. I did not prove it
by breaking `_restore_snapshot`, because that is product code and outside this
remit. The `assertNotEqual` and the snapshot assertion are what stop the test
passing vacuously; both were added for that reason.
