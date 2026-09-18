# Slice 021 — the module lockout with no way out

A product fix in `alvoraa_portal/alvoraa_portal/module_access.py`. Local only.
Approved by the user on 2026-09-18 for the release that is waiting to be pushed,
including the repair step and the tests.

## 1. The bug in one paragraph

`sync_permissions()` takes a tenant's permissions away **before** it records that
it did so. The record is a Single, `Alvoraa Access State`, and saving it can
fail. When it fails, the denial rows are already written, nothing says they
exist, and `sync_site` swallows the error and carries on to `apply_to_users()`,
which **commits**. The rows are then committed and unrecorded, and
`release_permissions()` can never remove them, because by design it releases only
what was recorded. The customer's modules are blocked and there is no supported
way to unblock them.

Slice 020 measured it on three doctypes: 0 rows → 3 rows → `release_permissions()`
returns `{'released': [], 'still_restricted': []}` with the 3 rows still there.

## 2. Why the save fails — found, not assumed

The docstring in `_save()` already blames a cached copy of the Single, and a fix
for that landed on 2026-09-07 (`d064b6a`) as a `doc.reload()`. **That fix is in
place and the error still fired five times on `test_site` on 18 September.** So
the stated cause was not the real one.

Two things I checked in the installed Frappe v16.33.1 source rather than
assuming:

* `frappe.get_single()` is **not** cached. It is `get_doc(doctype, doctype)`
  (`frappe/model/document.py:2385`), which reads the database. `get_cached_doc`
  is the cached one and nothing here calls it. The docstring's claim is wrong.
* `Document.reload()` → `load_from_db()` → for a Single,
  `frappe.db.get_singles_dict(self.doctype, for_update=self.flags.for_update)`
  (`document.py:252-268`). A **plain** SELECT unless `flags.for_update` is set.

And the check that throws, `check_if_latest()` (`document.py:1088`), compares the
copy in hand against a re-read done like this (`document.py:1432`):

```
self._doc_before_save = frappe.get_doc(self.doctype, self.name, for_update=True)
```

`for_update=True` on a Single becomes `SELECT ... FOR UPDATE` on `tabSingles`.

**That is the whole bug.** MariaDB InnoDB runs at REPEATABLE READ. Once
`sync_permissions` has read anything, its transaction holds a snapshot.

| Read | What InnoDB serves |
|---|---|
| `doc.reload()` — plain SELECT | the **snapshot**, so a change another connection committed since is invisible |
| `check_if_latest()` — SELECT … FOR UPDATE | a **locking read**, which always serves the **latest committed** row |

The two reads disagree by construction, so the mismatch is **deterministic**, not
bad luck. It fires whenever a second connection — another session's test run, a
second tenant sync, a background worker — writes that record while our
transaction is open.

Proved on `test_site` with two processes, one holding a transaction:

```
READER opened, modified=14:31:04.517420
WRITER wrote     modified=14:31:39.028080
READER plain reload      -> 14:31:04.517420     <- stale, the snapshot
READER FOR UPDATE reload -> 14:31:39.028080     <- the truth
PLAIN _save RAISED: TimestampMismatchError
```

The same sequence inside one process does **not** fail, because a connection
always sees its own writes. That is why it never reproduced on a quiet bench and
fired five times on a busy one.

## 3. Callers — grepped, whole repo

`alvox_compensation` is not in this tree. Nothing outside `alvoraa_portal` calls
any of these.

| Function | Production callers | Tests |
|---|---|---|
| `sync_site` | `tenant_api.py:619` (plan update) and `tenant_api.py:881` (provisioning), **both as `bench execute` strings**, both checking the return code and logging a warning — neither treats a failure as fatal | `test_module_access` 215/235, `test_tenant_setup` 17, `test_provision_guards` (source assertions only) |
| `sync_permissions` | only `module_access.py:197`, inside `sync_site`'s try/except | `test_access_control` ×15 |
| `release_permissions` | only `module_access.py:477` | `test_access_control` ×7, `test_tenant_setup` 31, `test_portal_security_010` 178 |
| `apply_to_users` | `module_access.py:210`, `tenant_setup.py:112` | `test_module_access` ×9, `test_subscription_access` 362 |
| `_save` | `module_access.py:440, 516` | `test_access_state_save` ×7 |

`hooks.py` has `doc_events` on **User** only, pointing at
`apply_on_user_insert` / `apply_on_user_update`. **No `scheduler_events`, no
`after_migrate`, no `after_install`, no `patches.txt` entry** touches module
access. Nothing runs `sync_site` unattended.

**What that means for part 3 of the fix:** letting `sync_permissions`' error out
of `sync_site` is safe. The only two production callers already read the exit
code of a `bench execute` and handle a non-zero result. No scheduler job, hook or
patch depends on it staying silent.

## 4. Persona impact

| Persona | Today | After |
|---|---|---|
| **CXO** | On a tenant that hit this, whole modules are dark and support cannot give them back | Nothing is ever denied without a record, so support can always give it back |
| **HR Manager** | Same — Payroll or Recruitment simply gone, no route to recovery | Same |
| **Employee** | Unaffected either way; the portal does not read this record | Unaffected |

## 5. HRMS domain impact

Only the desk permission gate. No leave, attendance, payroll or appraisal logic
changes. `Custom DocPerm` is the shared surface, and it is the one already owned
by this module.

## 6. Non-functional verdict on the proposed change

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** | One extra locking read of one small row per `_save`, on an operator-run command. The record-first order adds **one** `_save` before the loop and keeps the corrective one only when a doctype failed |
| Security | **improves** | A denial that no one can lift is a security fault in both directions: it withholds access a customer paid for, and it leaves permission state nobody can audit. The repair also refuses to touch a row that is not ours |
| Reliability | **improves** | The failure now has a defined end state: nothing written, error raised, operator told. Today it half-completes and reports success |
| Scalability | **neutral** | The locking read holds one row of `tabSingles` for the rest of the transaction, which serialises two concurrent syncs on the same site. That is the correct behaviour for a read-modify-write of the only record of what was taken away, and syncs are per-tenant and operator-driven |
| Maintainability | **improves** | The `_save` docstring currently blames the wrong cause; it is replaced with the measured one |
| Data integrity | **improves** | This is the whole point: the record and the rows can no longer disagree in the unsafe direction |
| Compliance / privacy | **improves** | No personal data anywhere near this code. The audit question "what did we deny this tenant, and when" gets an answer that is always true |

## 7. Parallel-work check

Incoming since I started: I fetched `origin/dev` at the start; local `dev` and
`origin/dev` are both `28622cf` and nothing new came in. Branch created from
`dev` at `28622cf`.

| File | Who else is in it | Plan |
|---|---|---|
| `module_access.py` | **nobody** — slice 020 explicitly did not change product code | Mine |
| `test_module_access.py`, `test_subscription_access.py`, `test_tenant_setup.py`, `test_access_control.py`, `test_permission_leak_020.py` | slice 020, not merged | **Not touched.** If my fix needed a change there I stop and ask |
| `test_access_state_save.py` | nobody, but it pins `_save` | Not touched. My change must keep its three tests passing |
| `tenant_api.py` | slice 010/012 history | Not touched |
| `hooks.py`, `patches.txt`, any DocType JSON | several slices | Not touched |
| The bench | slice 017 waiting, a release pass running | Taken only when free, one module at a time, released after |

New test file name `test_module_access_lockout_021.py` — sorts after
`test_module_access.py` and collides with nothing.

## 8. The proposed fix

### Part 1 — record the intent before writing the rows

Today the snapshot, the row writes and the record are one loop with the record
last. The proposal splits it:

1. work out `to_restrict` and take the snapshot of anything already customised
2. **`_save(restricted = already | to_restrict, snapshot = snapshot)`** — the
   record, before a single row is touched
3. write the rows
4. if any doctype failed, `_save` again to bring the record down to what actually
   landed

**On one transaction (revised during the build — see the implementation notes):**
they already are one, but holding the record open across the row loop holds the
state record's lock for the whole run and deadlocks two overlapping syncs. It was
measured happening. The record is therefore committed immediately; the safety
comes from the order, not from atomicity. Original reasoning below.

They already are one. `_save` writes `tabSingles` with
plain SQL and does not commit; the only `frappe.db.commit()` is at the end of
`sync_permissions`. What defeated it was not the transaction boundary — it was
`sync_site` swallowing the error and `apply_to_users()` committing afterwards.
Part 3 closes that. Record-first is the belt to that braces: if the record cannot
be made, **nothing has been written yet**, so there is nothing to strand even if
something later commits.

**Why over-recording is the safe direction.** If step 3 dies part-way, the record
names doctypes whose rows were never written. `release_permissions` on such a
doctype deletes rows that are not there (a no-op) and, if we snapshotted
originals, writes back exactly what was already present. Either way the doctype
ends where it started. Under-recording — today's behaviour — is the direction
that locks a customer out.

### Part 2 — fix the cause of the failed save

In `_save`, make the re-read a **locking** read:

```
doc.flags.for_update = True
doc.reload()
```

so it reads the same latest-committed row that `check_if_latest()` will read a
moment later, and holds that row until the transaction commits.

Why this and not the alternatives:

* **Not a retry loop** — it would hide a genuine concurrent write and could still
  lose the record.
* **Not `ignore_version` / switching the check off** — the check is the only
  thing standing between two syncs and a lost update on the only record of what
  we took away. Losing that update is the very bug being fixed.
* **A plain reload is not enough**, and that is measured (§2), not argued.

This is safe under concurrent calls precisely *because* it takes the lock: a
second sync on the same site blocks on the row until the first commits, then
reads the first one's result and adds to it. That turns two overlapping syncs
from a lost update into a queue.

### Part 3 — stop `sync_site` swallowing the error

`sync_site` keeps the `frappe.log_error` with a clear title, and then **re-raises**.
`apply_to_users()` never runs on a failed permission sync, so nothing commits
behind the failure. Checked against every caller (§3): both are `bench execute`
calls whose return code is already read and handled as a warning.

The other three `try/except` blocks in `sync_site` (workspaces, sidebars, navbar)
stay as they are. None of them denies anything or leaves anything unrecorded, so
none of them can lock a tenant out. Changing them is scope I have not been asked
for.

### Part 4 — the repair, and where it belongs

**A command HR support runs deliberately, not a patch on migrate.** The argument:

* A patch runs unattended on every site, including production, on every deploy.
  The thing it would edit is tenant permissions. The cost of getting that wrong
  is either a customer locked out or a customer given access they did not buy.
* The repair is a **one-off historical clean-up**. Parts 1–3 remove the cause, so
  after this release no new stranded rows can appear. A patch would keep running
  forever for a job that needs doing once.
* Nothing may run against a dev or production tenant without the user's word, and
  a patch is exactly a thing that runs without being asked.

Two functions, neither whitelisted (no HTTP surface, same as `sync_site`):

* `find_unrecorded_restrictions()` — reports, changes nothing.
* `repair_unrecorded_restrictions(apply=False)` — dry run by default.

**How a stranded row is told apart from a tenant's legitimate one.** Never a
blanket delete: `ppj.localhost` has 625 honest rows across 351 doctypes. A
doctype is a repair candidate only when **all** of these hold:

1. it has `Custom DocPerm` rows, and
2. it is **not** in `restricted_doctypes` (we do not admit to restricting it), and
3. it is one of the doctypes this site's plan blocks — the set
   `sync_permissions` could have touched, and
4. **every one of its rows is for an exempt role** (`System Manager`). That is the
   exact fingerprint `_keep_exempt_row()` leaves: one row, one exempt role, and
   nothing else. A tenant's own customisation, or the rows `hrms/setup.py` writes
   at install, always name other roles.

Anything with rows that fail (4) is reported as **suspect and left alone**.

**The honest limit.** If a stranded doctype had its own customisations before the
failed sync, those rows were deleted and the snapshot was lost in the same failed
save. Deleting the leftover exempt row returns it to Frappe's **standard**
permissions, not to the customisation. The repair says so per doctype, and where
a snapshot did survive it is put back verbatim instead. Restoring a lost
customisation exactly needs a database backup, and the report says which doctypes
are in that position.

## 9. Tests

New file `alvoraa_portal/alvoraa_portal/tests/test_module_access_lockout_021.py`,
each test proved to fail without the fix:

1. the record is written **before** the rows
2. a forced `_save` failure leaves **zero** stranded rows
3. `_save` re-reads the state record with a lock (the stale-Single case)
4. a failing `sync_permissions` comes **out** of `sync_site` instead of being
   swallowed
5. the repair releases only unrecorded, exempt-only rows and leaves a tenant's
   legitimate rows exactly where they were

## 10. What I will not do

* Not push anything, not merge into local `dev`, not touch any server or dev
  tenant.
* Not run the repair against `ppj.localhost` or any dev tenant.
* Not edit slice 020's five test files. If the fix turns out to need a change
  there, I stop and report it.
