# ALV-328 - DevOps inputs

Earlier sections for this slice live in `03-devops.md` (§3 Requirements, 12 Nov 2026, and
its Re-check). They stay as written. This file adds §5.

---

## §5 Release readiness - 12 Nov 2026

| | |
|---|---|
| Commit | `ccca2b6c` on `slice/alv-328-break-and-reason`, one commit on top of `origin/dev` `c5d57333`. Not pushed (Fact, `git log`, `git merge-base --is-ancestor`) |
| Author | `hrms-devops-engineer` |
| Verdict | **Ready with conditions** (listed at the end) |

**Bad news first.**

1. **Two release gates from the strategy have not run:** count E (does anyone outside HR add
   punches for other people at DTC today?) and count B (does any DTC role outside the HR list
   edit punches?). From this release, both are refused by the server. If either count is above
   0, someone at DTC loses a step they use. This is a production read, so Surbhi runs it.
2. **Nobody has opened the two screens in a browser yet** (implementation notes, "Known gaps").
   The JS was only syntax-checked. One browser pass on an own stack is needed before the dev push.
3. **This slice cannot reach `main` before ALV-326.** ALV-326 (`7e663d7f`, `4ae8499a`) is on
   `origin/dev` and not on `origin/main` (Fact, `git log origin/main..origin/dev`). Both will go
   to `main` in the same deploy. I did not find ALV-326's own migrate rehearsal in this worktree
   (`06-review.md` and `06-security.md` were not copied), so **I could not check** that it ran.

### What the commit changes, for running it

| Area | Changed? | Evidence |
|---|---|---|
| New Custom Field on HR Settings (`alvoraa_manager_sees_whole_line_punches`, Check, default 0) | Yes | Fact, `git show ccca2b6c -- field_app_settings.py`, added to the existing `after_migrate()` list |
| `hooks.py` | No | Fact, `git diff --stat c5d57333 ccca2b6c -- hooks.py` empty. `field_app_settings.after_migrate` is already in `after_migrate` (line 622) and `after_install` (line 702) |
| `patches.txt`, any DocType JSON, fixtures | No | Fact, same `git diff --stat` on `*.json`, `*patches.txt` empty |
| Custom DocPerm or User Permission rows | No | Fact, no file writes them. Punch rights change in code only: `checkin_has_permission` and `checkin_query_conditions` in `field_app_access.py` |
| `deploy/` (including `nginx.conf`) | No | Fact, `git diff --stat ... -- deploy/` empty |
| Assets | `portal.js` (+61 lines), `panels.css` (+6 lines) | Fact, `git show --stat` |
| New job, queue, container, secret, endpoint | No | Fact, read the diff |

### OPS items checked against `ccca2b6c`

| ID | Status | Evidence |
|---|---|---|
| OPS-1 no Checkin query per day | **Met** | `QueryCounts` in `test_break_and_reason_alv328.py`: `month()` same total for 2-punch and many-punch person, one own Checkin read; `person()` same total for 1 and 12+ months, exactly one Checkin read. Green on fresh site `test328` (notes, AC-46/47). I did not re-run it |
| OPS-2 rule set and allowance once per request | **Met** | Strategy §6: `breaks_by_day` calls `rule_set_for`, `prepare`, `_employee_flags` once, then loops in memory. The constant-count test above would fail if this moved into the loop |
| OPS-3 count asserted as a property | **Partly** | The property is asserted. The before/after numbers were not written as figures: the notes say "a constant handful", not a count. P3 - write the two numbers in the notes |
| OPS-4 small payload | **Met** | AC-48 test (line 232); keys only when set, per notes |
| OPS-5 no index | **Met** | No index added. Note: the punch scope is now an `IN (subquery)`, with a recursive one when the switch is on. Not measured at DTC size; the switch is off at release, so only the plain subquery runs. FYI |
| OPS-6 / OPS-6a migrate via `after_migrate` + `after_install` | **Met** | See "Migrate" below |
| OPS-7 no manual build or `assets.json` bump on servers | **Met** | No build step added. The deploy runs `scripts/refresh_bench_files.sh` (Fact, `deploy.yml` line 505), which copies assets and writes a new `assets.json` (Fact, line 67) |
| OPS-8 / OPS-8a rollback by revert, untick first | **Met as written in strategy §13**; not exercised | See "Rollback" |
| OPS-9 / OPS-9a per-tenant checks | **Not met yet** - by design, they run after each deploy | See "Checks after release" |

### Migrate - yes, and it runs by itself safely

- **Needed:** yes, for one Custom Field. The deploy already runs `bench --site all migrate`
  on every dev and main deploy (Fact, `deploy.yml` line 159). Nothing to add by hand.
- **New tenants:** `after_install` runs the same function, so `install-app` creates the field
  too. Proven by AC-28 on a fresh site with no migrate (Fact, notes line 34-36, 87).
- **Safe to run twice:** `create_custom_fields` updates in place and never writes a value.
- **Cheap:** HR Settings is a Single, so this is one `tabCustom Field` row and no
  `ALTER TABLE` (Fact, from the Re-check in `03-devops.md`).
- **Lands off:** nothing writes the value, so it reads as missing or 0. `whole_line_on()` treats
  missing or any error as off (Fact, code).
- **Not the 5 Nov job-queue trap.** That migrate deleted 1,780 permission rows and filled the
  job queue. This one deletes nothing and writes no permission row (Fact, the diff). **Inference:**
  no queue load beyond a normal migrate.
- **Import order:** `field_app_settings` now imports `WHOLE_LINE_SETTING` from `field_app_access`;
  `field_app_access` imports only `frappe` (Fact, grep). No import loop.

### Assets - what the release must do

- **On dev and main: nothing by hand.** No `bench build`, no `docker cp`, no `assets.json` touch.
  The image builds the app and `refresh_bench_files.sh` replaces the volume's assets and
  `assets.json`, which changes the `?v=` number. (The stale-volume trap from 23 Sep is
  answered by that script.)
- **Check after each deploy:** the `?v=` number on `/hrms-employee` changed, and the served
  `portal.js` contains "Break not measured" (OPS-7).
- **Local only:** if Surbhi tests on a bench by copying files, `touch sites/assets/assets.json`
  and `clear-cache` after the copy, each on her approval.

### Order

1. Browser pass on an own stack (not `hrlocal-bench` - it mounts the stale main checkout).
2. **Dev push, on Surbhi's word.** Before it: `gh run list --branch dev --limit 4` - today the
   last CI and Build Image for `c5d57333` are **completed, success** (Fact, run 12 Nov 2026,
   17:06 UTC start). If a run is in progress, wait for it to finish. Then
   `git fetch origin dev && git rebase origin/dev`, read any incoming commits, then push
   with `git push origin slice/alv-328-break-and-reason:dev`. One push, not several.
3. After the dev deploy: the checks below on every dev site, plus the API probe.
4. Counts E and B on production DTC (Surbhi runs them). If either is above 0, stop and decide D1/D2.
5. **Main, on Surbhi's word, after dev testing.** It carries ALV-326 and ALV-328 together.
   Take the "before" counts first, then deploy, then the checks again.

### Checks after release - read-only, for Surbhi to run

Quoted, not run. For each site in the stack, inside the backend container. Capture stdout and
stderr (lesson 8). Take the two permission counts **before** the deploy and save them.

```sh
# list sites: ls sites | grep '\.' | grep -v assets   (check the list by eye)
SITE=<site>
bench --site "$SITE" mariadb 2>&1 <<'SQL'
-- 1. field exists: expect 1
SELECT COUNT(*) AS field_rows FROM `tabCustom Field`
 WHERE dt='HR Settings' AND fieldname='alvoraa_manager_sees_whole_line_punches';
-- 2. switch off: expect no row, or 0
SELECT value FROM tabSingles
 WHERE doctype='HR Settings' AND field='alvoraa_manager_sees_whole_line_punches';
-- 3. permission rows unchanged: compare with the "before" numbers
SELECT COUNT(*), MAX(modified) FROM `tabCustom DocPerm`;
SELECT COUNT(*), MAX(modified) FROM `tabUser Permission`;
-- 4. Custom DocPerm on Employee Checkin, by role (count B; same before and after)
SELECT role, `read`, `write`, `create`, `delete` FROM `tabCustom DocPerm`
 WHERE parent='Employee Checkin' ORDER BY role;
SQL
```

5. In the repo: `git diff --stat origin/main -- deploy/nginx.conf` before the main push - expect
   empty (for dev, compare with the commit dev ran before).
6. Manager sees only direct reports' punches - in `bench --site "$SITE" console`, read-only:

```python
mgr_user = "<a manager's login, not HR>"
emp = frappe.db.get_value("Employee", {"user_id": mgr_user}, "name")
direct = set(frappe.get_all("Employee", {"reports_to": emp, "status": "Active"}, pluck="name")) | {emp}
frappe.set_user(mgr_user)
seen = set(frappe.get_list("Employee Checkin", pluck="employee", distinct=True, limit_page_length=0))
print("PASS" if seen <= direct else "FAIL", len(seen), len(direct), sorted(seen - direct)[:5])
```

7. On dev only, as `data-doors.md` asks: the same manager login calls
   `GET /api/resource/Employee Checkin?limit_page_length=0&fields=["employee"]` and sees only
   the IDs in `direct`; and a `PUT` on a report's punch returns 403.
8. Assets: `?v=` changed; `portal.js` contains "Break not measured".

All lines print PASS/FAIL or a count. None writes anything.

### Rollback

1. If anyone ticked the switch, untick it in HR Settings first (a data change, on Surbhi's word).
   Otherwise a later redeploy turns whole-line access on again at once.
2. `git revert ccca2b6c` on `dev`, push on her word, let Deploy run. Same for `main` if it got there.
3. **Do not** redeploy the previous image tag: that would also undo ALV-326.
4. Leave the Custom Field. It does nothing without the code. Deleting it is optional tidying.
5. Tell DTC: a rollback gives managers edit and delete on their reports' punches again
   (ALV-332/333 reopen).
6. Time: the deploy loop still waits about 7 minutes for `bench version` (lesson 22, measured
   22 Sep). **I could not check** today's full deploy time, so I cannot say the rollback fits
   the 15-minute budget.

### Findings

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-10 | Run counts E and B on production DTC before the main push; if either is above 0, decide D1/D2 first | The server now refuses punch edits outside HR | Someone at DTC is blocked mid-month with no warning | P1 · Recommend | |
| OPS-11 | One browser pass of both screens on an own stack before the dev push | JS only syntax-checked | A broken Attendance page on dev | P1 · Recommend | |
| OPS-12 | Push to `main` only with or after ALV-326, and confirm ALV-326's migrate rehearsal exists | ALV-328 calls ALV-326 code; I could not find its rehearsal | A main deploy whose migrate was never tried | P2 · Recommend | |
| OPS-13 | Run the checks above after the dev deploy and after the main deploy, on every site | Proves the switch is off and no row moved | A tenant with access nobody chose (ALV-249 shape) | P1 · Recommend | |
| OPS-14 | Write the measured query counts (before and after) in the implementation notes | OPS-3 asks for the number, not only the property | Next slice cannot tell if it grew | P3 · Consider | |

### What I ran and what I quoted

- **Ran (read-only):** `git show`, `git diff --stat`, `git log origin/main..origin/dev`,
  `git merge-base`, greps on the worktree, `gh run list --branch dev`.
- **Quoted, not run:** every bench, SQL, console, API and push line above.
- **Measured today:** nothing. No number in this section is new.
- **Left behind:** this file only, not committed. No container, setting or bench touched.

### Subtract pass

Removed: a migrate dry run on a copy of DTC (a Single adds no column); a load test of the
recursive subquery (switch is off at release); a separate `assets.json` step (the deploy does
it). Nothing else removed.

### Conditions for "Ready"

1. Browser pass of both screens on an own stack before the dev push.
2. Dev push only after the running dev CI finishes, after fetch and rebase, as one push.
3. The checks above PASS on every dev site, plus the manager API probe.
4. Counts E and B on DTC are 0, or D1/D2 decided, before the main push.
5. Main carries ALV-326 with it; ALV-326's migrate rehearsal is confirmed.
6. Rollback is by revert with the switch unticked first, never by previous image tag.
