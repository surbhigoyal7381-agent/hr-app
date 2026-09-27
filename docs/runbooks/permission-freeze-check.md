# Runbook · Permission freeze check (ALV-127)

**After any permission change made in the Desk, run the permission freeze check on that
tenant.**

```bash
bench --site <site> execute alvoraa_portal.permission_health.check_permission_freeze
```

It reads only. It is safe on a live tenant, it changes nothing, and it reads no
employee's data — only role names and permission flags.

## Why

Frappe keeps two sets of permission rows: the standard ones that ship with Frappe HR,
and the tenant's own `Custom DocPerm` rows. **The moment one custom row exists for a
doctype, Frappe ignores that doctype's standard rows for ever.** The doctype is frozen:
a later `bench migrate` will not change it, and nobody is told.

Granting a role in the Role Permissions Manager copies every standard row in first, so
nobody loses access that day. Two things after that do change access, silently:

- deleting a row in that same screen, or pressing **Reset to default**;
- a single `Custom DocPerm` written by code, a fixture or a patch — that leaves the
  doctype in custom mode holding only that one row.

## What we found while building this, and it was not what the ticket said

**Three of the four watched doctypes are frozen on every site we build, from the moment
it is installed.** Nobody has to touch anything.

Measured on 2026-09-25 on a site created from scratch and never opened by a human:
`Attendance Request` 5 custom rows, `Attendance` 5, `Leave Application` 9,
`Employee Performance Feedback` 0. The chain is Frappe HR's own:

```
hrms/setup.py:637   get_user_types_data()   lists Attendance Request, Leave Application …
hrms/setup.py:693   create_user_type()      saves the "Employee Self Service" User Type
frappe/core/doctype/user_type/user_type.py:161   add_permission(doctype, role, 0)
                                            -> setup_custom_perms -> copy_perms
```

So **the 5 rows on `dtc.alvoraa.co` are our install, not a tenant's administrator** —
and `Employee Performance Feedback` has 0 there for the same reason it has 0 here: it is
not on Frappe HR's ESS list. Nothing was misconfigured by anyone.

That does not make the freeze harmless. It means the freeze is our baseline, and an
upstream permission fix to any of those three will never arrive by itself on any site we
run. The check separates "frozen the way every site is" from "somebody changed it".

## Reading the result

| Status | What it means | What to do |
|---|---|---|
| `ok` | The doctype still follows Frappe HR's own permissions. | Nothing. |
| `frozen_at_install` | Frozen, but only by our own install — the rows are the standard ones plus `Employee Self Service`. This is what a healthy site looks like. | Nothing. |
| `frozen` | Somebody changed it: a role was granted or lost beyond the install. Nobody has lost read, but the doctype no longer tracks Frappe HR. | Check the change was intended, then record it. Re-check by hand whenever Frappe HR changes that doctype's permissions upstream. |
| `broken` | `Employee` or `HR Manager` has no read row at permlevel 0, or a watched doctype is not installed. | Act today. Somebody's screen has stopped working. The report names the role and the screen to fix it in. |

An `if_owner` row does not count as the role having read — it grants read only on records
the user created, which is narrower, and counting it would let a real loss of access pass
as healthy.

The report also prints **how much it read** — doctypes, standard rows, custom rows. If
those counts are zero the check raises instead of reporting OK, because a check that
passes having read nothing looks exactly like a clean site.

## When to run it

- After any permission change made in the Desk, on that tenant.
- After every deploy that runs `bench migrate`, on each tenant.
- When somebody reports that a queue or a list has gone empty for one role.

## The list it watches

`WATCHED_DOCTYPES` in `alvoraa_portal/alvoraa_portal/permission_health.py`, each with the
reason it is there. Adding a doctype is cheap and safe — the check is read-only — so err
towards adding. A doctype on the list that is not installed is reported as an error, never
skipped.
