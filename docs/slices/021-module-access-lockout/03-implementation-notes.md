# Slice 021 — implementation notes

Local only. Nothing pushed, nothing merged into local `dev`, no server or dev
tenant touched.

## 1. What I built, file by file

### `alvoraa_portal/alvoraa_portal/module_access.py` — the only product file

| Change | Mechanism | Why |
|---|---|---|
| `sync_permissions()` — snapshot, then **record**, then write the rows | **extend** existing code, reorder | A failure at the record step now leaves nothing denied |
| `sync_permissions()` — `still_recorded`, re-read after the release | **fix** | The old `already` was the *pre-release* set; adding it back would have re-restricted everything an upgrade had just freed |
| `_save()` — `doc.flags.for_update = True` before `reload()` | **extend**, one line | The real cause of the failed save (§2) |
| `sync_site()` — logs and **re-raises** instead of swallowing | **extend** | Nothing commits behind a failed permission sync |
| `find_unrecorded_restrictions()` — new, **read-only** | **build** | The question support asks first, with no power to delete |
| `repair_unrecorded_restrictions()` — new, dry run by default | **build** | The deliberate fix for anything already stranded |
| `_rows_by_doctype()` — new helper | **build** | One query per 500 doctypes instead of one per doctype |
| `_snapshot_many()` — new helper | **build** | The snapshot step was two queries per doctype — 900 round trips on a Starter tenant. Now one per 500 names |

### `alvoraa_portal/alvoraa_portal/tests/test_module_access_lockout_021.py` — new

17 tests in five classes. Every one proved to fail without the fix it pins (§6).

Nothing else changed. Not `hooks.py`, not `patches.txt`, no DocType, no
`tenant_api.py`, and **none of slice 020's five test files**.

## 2. Why the save was failing — and why the previous fix was not it

`_save()` already carried a `doc.reload()`, added on 2026-09-07 (`d064b6a`)
against a docstring that blamed a cached copy of the Single. **Both parts of that
were wrong, and the error still fired five times on `test_site` on 18 September.**

Checked in the installed Frappe v16.33.1 source, not assumed:

* `frappe.get_single()` is not cached — it is `get_doc(doctype, doctype)`
  (`frappe/model/document.py:2385`). `get_cached_doc` is the cached one and
  nothing here calls it.
* `Document.reload()` → `load_from_db()` → for a Single,
  `frappe.db.get_singles_dict(self.doctype, for_update=self.flags.for_update)`
  (`document.py:252-268`) — a **plain** SELECT unless the flag is set.
* `check_if_latest()` (`document.py:1088`) compares against
  `frappe.get_doc(self.doctype, self.name, for_update=True)` (`document.py:1432`)
  — a **locking** read.

MariaDB InnoDB runs at REPEATABLE READ. Once `sync_permissions` has read
anything, its transaction holds a snapshot. A plain read serves the snapshot; a
locking read always serves the latest committed row. So the two reads Frappe
makes **disagree by construction** whenever another connection has committed a
change — another session's test run, a second sync, a worker. The mismatch was
deterministic, not unlucky, which is exactly why it never reproduced on a quiet
bench and fired repeatedly on a busy one.

Measured on `test_site`, one process holding a transaction and a second writing:

```
READER opened, modified=14:31:04.517420
WRITER wrote     modified=14:31:39.028080
READER plain reload      -> 14:31:04.517420     <- stale
READER FOR UPDATE reload -> 14:31:39.028080     <- the truth
PLAIN _save RAISED: TimestampMismatchError
```

**The fix** is one line: `doc.flags.for_update = True` before `doc.reload()`. We
then read the row the guard will compare against, and hold it until commit.

Not a retry loop and not `ignore_version`: both would hide a genuine concurrent
write, and the update they would lose is the only record of what we took away —
the very bug being fixed. Under concurrent calls the lock is what makes it safe:
a second sync blocks on the row until the first commits, then reads the first
one's answer and adds to it. Two overlapping syncs become a queue instead of a
lost update.

## 3. The order now

```
release what the plan no longer blocks        (commits, as before)
still_recorded = what is recorded AFTER that
snapshot every doctype about to be taken
_save(still_recorded | to_restrict, snapshot); commit   <- THE RECORD
for dt in to_restrict: delete rows; keep one exempt row
if any failed: _save(still_recorded | restricted, snapshot)   <- correct it down
frappe.db.commit()
```

**On one transaction — I checked, and then deliberately chose not to.** They
already were one: `_save` writes `tabSingles` with plain SQL through
`update_single` and does not commit, and the only `frappe.db.commit()` was at the
end of `sync_permissions`. What defeated it was never the boundary; it was
`sync_site` swallowing the error and `apply_to_users()` committing afterwards,
which part 3 closes.

But holding the record open across the row loop turned out to be actively
harmful. `_save` now takes a **locking** read of the state record (§2), and
record-first would hold that lock across all 450 row writes — seconds to
minutes. Two syncs overlapping on one site would then deadlock: each holding
permission rows the other wants while waiting for the record. **Measured**, not
theorised: a `QueryDeadlockError` on `tabCustom DocPerm` when this suite ran
alongside another session's full run.

So the record is committed immediately. The safety comes from the **order**, not
from atomicity — if the record cannot be made, not one row has been touched; if
the rows fail afterwards, we have over-recorded, which is the safe direction.
Committing also makes the record durable against the process simply dying, which
an open transaction is not.

**Over-recording is the safe direction.** If the loop dies part-way, the record
names doctypes whose rows were never written. Releasing such a doctype deletes
rows that are not there (a no-op) and, where we snapshotted originals, writes
back exactly what was already present. Either way it ends where it started.
Under-recording — the old behaviour — is the direction that locks a customer out.

I did **not** add a rollback. With record-first there is nothing to roll back at
the point of failure, and a rollback inside `sync_permissions` would discard
whatever the caller had pending. Less blast radius for the same guarantee.

## 4. What a caller sees when it fails

`sync_site` logs `module_access: permission sync failed - site NOT synced` with
the traceback, prints a line the operator sees on the terminal, and **raises**.
`apply_to_users()` never runs, so nothing commits behind the failure.

Checked every caller in the whole repo first:

| Caller | What it does now | Effect of the raise |
|---|---|---|
| `tenant_api.py:619` (plan update) | `bench execute`, checks `returncode != 0`, `frappe.log_error`, **not fatal** | A warning is logged; the plan change still stands |
| `tenant_api.py:881` (provisioning) | `bench execute`, on non-zero appends `[WARN] module access not applied` to the log | The provision still completes with a visible warning |
| `tenant_setup.py:112` | calls `apply_to_users` only | unaffected |
| `hooks.py` `doc_events` on User | `apply_on_user_insert` / `apply_on_user_update` | unaffected |
| `scheduler_events`, `after_migrate`, `after_install`, `patches.txt` | **no entry anywhere** | nothing runs this unattended |

So nothing depended on the silence. The trade is stated plainly: a failed sync
now leaves the tenant seeing **too much** rather than too little, and says so
loudly. That is the right way round — a visible over-exposure of desk menus is a
support call; an invisible lockout is a customer who cannot work.

The other three `try/except` blocks in `sync_site` (workspaces, sidebars,
navbar) are left swallowing. None of them denies anything or leaves anything
unrecorded, so none can lock a tenant out. Changing them is scope I was not
asked for.

## 5. The report and the repair

### `find_unrecorded_restrictions()` — read-only, safe anywhere

```
bench --site acme.alvoraa.co execute \
    alvoraa_portal.module_access.find_unrecorded_restrictions
```

Reads only. No INSERT, UPDATE or DELETE, no commit, no cache clear — pinned by a
test that spies on `frappe.db.sql` and `frappe.db.commit` and compares the row
count and the state record's `modified` before and after. Safe to run against a
live tenant, including production, at any time. It is deliberately a separate
function from the repair so that seeing the answer never requires holding a tool
that can also delete.

**How it tells a legitimate row from a stranded one.** A doctype is stranded only
when both hold:

1. it is **not** in `restricted_doctypes` — we do not admit to restricting it, and
2. **every** one of its `Custom DocPerm` rows names an exempt role (System Manager).

(2) is the exact fingerprint `_keep_exempt_row()` leaves: one row, one exempt
role, nothing else, because `sync_permissions` deletes all the others first.
Every legitimate source names some other role — `hrms/setup.py`'s
`add_default_hr_permissions` writes HR Manager and HR User rows at install, and
the Employee Self Service `User Type` generates rows for about 22 doctypes. One
such role anywhere in a doctype's rows is enough to class it legitimate.

Measured while proving this on a real strand: **365 doctypes carried rows, 319
matched the fingerprint, and all 46 of the rest — every one an Employee Self
Service or HR grant — were correctly left alone.**

**What it cannot tell, said plainly:**

* A tenant administrator who hand-made a single System-Manager-only row on a
  doctype has built the same shape by hand, and the report will call it
  stranded. `first_seen` (the earliest row's creation date) is reported to help —
  a genuine strand is dated when a plan was changed, an install-time row when the
  site was built — but nothing in the data settles it. That is precisely why the
  repair is a separate, deliberate act and not a patch.
* It cannot say what was there **before** a stranded doctype was denied. If the
  snapshot was lost in the same failed save that lost the record, that is gone;
  `restores` says which doctypes are in that position.
* It does not judge whether a denial was correct. A doctype the plan really
  should deny is still stranded if nothing recorded it, because nothing can give
  it back.

**Scope:** the report scans **every** doctype on the site that has any
`Custom DocPerm` row, wider than the current plan's blocked list on purpose — a
strand left by a plan the tenant has since moved off sits outside it, and is
exactly what support is looking for. Each entry says `in_current_plan` so the
operator can see which plan left it.

### `repair_unrecorded_restrictions()` — deliberate, dry run by default

```
bench --site acme.alvoraa.co execute \
    alvoraa_portal.module_access.repair_unrecorded_restrictions \
    --kwargs "{'apply': 1}"
```

**Read wide, write narrow.** The repair is bounded to the doctypes this plan
blocks unless an operator names them, because those are the only ones
`sync_permissions` could have written. The report prints the names to pass for
anything outside it.

Where the snapshot survived, the original rows go back verbatim. Where it did
not, deleting the leftover exempt row returns the doctype to Frappe's **standard**
permissions, which is not what was there if the tenant had customised it. The
report names every doctype in that position. Being on standard permissions still
beats being locked out; restoring a lost customisation exactly needs a backup.
A `Custom DocPerm` a tenant recorded through `release_permissions` is left to
that function; this one never touches it.

### Why a command and not a patch on migrate

* A patch runs unattended on every site including production, on every deploy,
  and the thing it edits is tenant permissions. The cost of a wrong call is a
  customer locked out or a customer given access they did not buy.
* Parts 1–3 remove the cause, so this is a **one-off historical clean-up**. A
  patch would keep running forever for a job that needs doing once.
* The report cannot always be certain (§5), so a human should see the list before
  anything is deleted. A patch cannot show anyone anything.

## 6. Tests, and the fail-without-fix proof

`alvoraa_portal/alvoraa_portal/tests/test_module_access_lockout_021.py`, 17
tests. Bounded to three payroll doctypes so it runs in seconds and leaves a
shared bench alone; every class restores what it changed, registered with
`addCleanup` **before** the write.

Proof run by piping a script on stdin that switches each fix off in-process and
re-runs the same suite (never `docker cp`):

| Switched off | Tests that fail |
|---|---|
| — nothing (the fix as shipped) | **0 of 17** |
| record before rows | `test_a_failing_save_leaves_nothing_denied`, `test_the_record_is_written_before_the_first_row` |
| the locking re-read | `test_the_reread_is_a_locking_read` |
| the error not being swallowed | `test_sync_site_no_longer_swallows_a_permission_failure`, `test_nothing_commits_behind_the_failure`, `test_the_failure_is_logged_with_a_title_support_can_find` |
| the report and the repair | all 9 of their tests |

Two of those tests needed correcting before they proved anything, and both are
worth recording:

* `test_a_failing_save_leaves_nothing_denied` originally ended with
  `frappe.db.rollback()` and passed with the fix switched off — the rollback hid
  the damage. The real sequence **commits** afterwards (that is what
  `apply_to_users()` did), so the test now commits and then checks. It fails
  without the fix.
* `test_the_reread_is_a_locking_read` originally asserted "a locking read
  happened", which is true without the fix too, because Frappe's own
  `check_if_latest()` always does one. It now counts them: one means the old
  stale plain reload, two means the fix.

### The repair proved on a real strand

Not a fixture. A full `test_access_control` run on this branch left `test_site`
genuinely stranded, and the repair was run against it:

| | rows | doctypes | recorded |
|---|---|---|---|
| before | 551 | 365 | 0 |
| after `repair_unrecorded_restrictions(apply=1)` | 232 | 46 | 0 |
| re-check | stranded **0**, legitimate 46 | | |

319 released, 0 restored from snapshot (the snapshots were lost with the
record — the honest limit in §5), and every one of the 46 legitimate
Employee Self Service and HR grants untouched.

### Other suites

| Module | Result |
|---|---|
| `test_module_access_lockout_021` (new) | **17 tests, OK** |
| `test_access_state_save` (pins `_save`) | **3 tests, OK** — the existing pin still holds |
| `test_access_control` (pins sync/release) | 34 tests, **2 failures, neither mine** — see §8 |

## 7. The seven dimensions, against the code I actually wrote

| Dimension | Before → after | Why |
|---|---|---|
| Performance | **improves** | One extra locking read of one small row per `_save`, and one extra `_save` per run, on an operator-run command — set against the snapshot step going from about 900 queries to 2 on a 450-doctype sync. The report costs 1 query per 500 doctypes plus one `creation` lookup per *stranded* doctype, not per doctype |
| Security | **improves** | A denial nobody can lift withholds access the customer paid for and leaves permission state nobody can audit. The repair refuses to touch a row that is not ours, and the report has no power to write at all |
| Reliability | **improves** | The failure has a defined end state: nothing written, logged with a findable title, raised to a caller that already handles it. It used to half-complete and report success |
| Scalability | **improves** | The first cut of this change made it worse and the bench proved it: the locking read plus record-first held the state record across all 450 row writes, and two overlapping syncs deadlocked. Committing the record at once shrinks the lock to a moment. Net against the old code, the snapshot step also drops from ~900 queries to ~2, so a 450-doctype sync is materially lighter than before |
| Maintainability | **improves** | The `_save` docstring blamed a cause that was not real and a fix that did not work. It now carries the measurement |
| Data integrity | **improves** | The point of the slice: the record and the rows can no longer disagree in the unsafe direction |
| Compliance / privacy | **improves** | No personal data anywhere near this code, and none is logged — the repair's audit entry carries doctype names only. "What did we deny this tenant, and when" now has an answer that is always true, and support can ask it on production without being handed a delete |

## 8. What else moved while I worked

* **Nothing came in from others on the branch.** I fetched `origin/dev` at the
  start; local `dev` and `origin/dev` were both `28622cf` and stayed there. No
  rebase was needed, no conflicts, nothing of anyone else's to preserve.
* **Another session dropped and rebuilt `test_site` mid-run**, at about 09:29
  server time: `bench --site test_site install-app erpnext hrms alvoraa_portal
  alvoraa_goals` (pid 31262 in `hrlocal-bench`), after the site directory was
  recreated at 09:28. A `test_access_control` run of mine collided with it and
  returned 26 errors against a site that was momentarily frappe-only. **That is
  not a code fault and not my damage.** I stood down, marked the board, waited
  for the rebuild and re-ran.
* **Two pre-existing `test_access_control` failures**, both confirmed not mine by
  running the same test against the unfixed `dev` code on the same site:
  * `test_it_restores_pre_existing_customisations_exactly` — "this test needs a
    doctype that has custom perms". Already reported by slice 020: an earlier
    blanket delete removed the install-time rows.
  * `test_business_grants_recruitment_back` — "Job Opening is included in
    Business". Job Opening was among the 551 stranded rows on the site at the
    time. **Fails identically on the unfixed code.**
* I did not touch slice 020's five test files. Nothing in my fix needed a change
  there — `test_access_state_save.py`'s three tests still pass unchanged.

## 9. Commands I ran

All bench work in a throwaway container `hrlocal-021` mounting this worktree
(the shared bench mounts the main checkout), taken only when `run-tests` was
clear, one run at a time, and removed afterwards. Probes were piped on stdin to
the bench virtualenv's python; **no `docker cp`, no server, no dev tenant**.

```
bench --site test_site run-tests --module alvoraa_portal.tests.test_module_access_lockout_021
bench --site test_site run-tests --module alvoraa_portal.tests.test_access_state_save
bench --site test_site run-tests --module alvoraa_portal.tests.test_access_control
python scripts/check_app_integrity.py        -> 580 checks, OK - all consistent
```

## 10. Known gaps and shortcuts, declared

1. **The two-process proof is not a test.** The stale-Single failure needs two
   database connections, and the pinned test asserts the *mechanism* (two
   locking reads instead of one) rather than reproducing the race. The
   end-to-end two-process reproduction is in §2, run by hand. A test that spawns
   a second connection would be a better proof and a worse citizen on a shared
   bench; I chose the citizen.
2. **`sync_permissions(only=...)` still over-releases.** With `only` set,
   `should_block` is narrowed *before* the release-before-restrict step, so a
   run bounded to three doctypes releases every other recorded restriction on
   the site. That is pre-existing, it is what the test suites rely on, and it is
   not what I was asked to fix — but it is a landmine and someone should look at
   it.
3. **The report cannot always be certain** (§5). A hand-made System-Manager-only
   row looks identical to a strand. `first_seen` helps; nothing settles it.
4. **The repair cannot restore a lost customisation** (§5), only standard
   permissions, where the snapshot went with the record.
5. **The fingerprint assumes `ADMIN_ROLES` has not changed.** If a future release
   adds an exempt role, rows written under the old set would no longer be
   exempt-only and the report would call them legitimate. Worth a note wherever
   `ADMIN_ROLES` is edited.
6. **No full-suite run.** I ran the new module and the two that pin this code. A
   clean full `alvoraa_portal` and `alvoraa_goals` pass is still owed, and is
   best done after the rebuilt `test_site` settles and slice 020's test fixes
   are merged — until they are, `test_module_access` and friends will strand the
   site again on every run.
