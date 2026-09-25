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

Measured read-only on production on 2026-09-25: `dtc.alvoraa.co` already has 5 custom
rows on `Attendance Request`. It is already frozen. Nothing is broken today.

## Reading the result

| Status | What it means | What to do |
|---|---|---|
| `ok` | The doctype still follows Frappe HR's own permissions. | Nothing. |
| `frozen` | Custom permissions are in force. Nobody has lost access, but upstream permission fixes will never reach this tenant. | Record it. Re-check by hand whenever Frappe HR changes that doctype's permissions upstream. |
| `broken` | `Employee` or `HR Manager` has no read row, or a watched doctype is not installed. | Act today. Somebody's screen has stopped working. The report names the role and the screen to fix it in. |

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
