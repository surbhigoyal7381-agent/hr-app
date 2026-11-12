# ALV-328 - DevOps and performance requirements

| | |
|---|---|
| Slice | ALV-328 (rides on ALV-326, branch `slice/alv-326-shift-hours`, already on `origin/dev` at `4ae8499a` - Fact, `git branch -r --contains HEAD`, 12 Nov 2026) |
| Stage | §3 Requirements - for the business analyst to trace into stories |
| Author | `hrms-devops-engineer`, 12 Nov 2026 |
| Reads | `01-product-brief.md`, `02-design.md`, `nfr-budget.md` §2-3, the code named below |

**Bad news first.**

1. **The obvious way to build this is an N+1.** `payroll_rules_apply._punches(employee, date)`
   runs one Employee Checkin query per person per day (Fact, read at line 365). Called once
   per day it adds 31 queries to `month()` and up to 365 to `person()`. OPS-1 says how to
   reuse the engine's rules without that.
2. **A rollback by image tag would also undo ALV-326** if both ship in one deploy. OPS-8
   says how to undo ALV-328 alone.

No new container, job, queue, cache, setting, secret, nginx route or permission row. This
is a display change on two existing endpoints and two existing screens.

---

## §3 Requirements - 12 Nov 2026

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | **No Employee Checkin query per day.** `month()` already reads the whole month's punches in one `get_list` (Fact, `attendance_correction.py` ~512); compute each day's break from those rows - zero extra Checkin queries. `person()` reads no punches today (Fact, `attendance_analytics.py` 602-662); add exactly **one** Checkin read for its whole range. To keep "same rules as the engine", split the part of `_punches` after the query (whole minutes → `collapse_duplicate_punches` → `break_gaps`) into a small pure helper that the engine and both screens call. The engine keeps its own query. Group by **calendar date** and whole minutes, like the engine (brief R2). | `nfr-budget` §2: "no query inside a loop"; the count must be the same for 20 days as for 365. | 31 extra queries per Attendance page open; up to 365 on a 12-month Insights view. At pay week every DTC employee opens the page at once. | P1 · Recommend | |
| OPS-2 | **Read the allowance and the "shift hours only" switch once per request, not per day.** Use `rule_set_for(company)` then `day_rules_on(...)` (or `prepare` + `_employee_flags`) once; reuse `month()`'s existing `shift_cache` for the shift start and end. | The allowance is per category, which is per person, not per day (Fact, `_employee_flags` line 286). `prepare` reads the rule set, all Shift Types and the holiday list (Fact). | `prepare` in a day loop is several queries times 31. | P1 · Recommend | |
| OPS-3 | **Assert the query count as a property, in a test.** `month()`: the same count for a month of 2-punch days and a month of 6-punch days. `person()`: the same count for 1 month and 12 months. Record the before and after numbers in the notes. The engineer measures them; I did not. | `nfr-budget` §2: "assert the property, record the number". | A loop slips in later and nobody sees it. | P2 · Recommend | |
| OPS-4 | **Keep the payload small: send a key only when it has a value.** `break_*` only on days with a figure; `rules_why` and `evaluated_on` only when set; no `rules_why` in `person()` (design §5). **Estimate:** `month()` +12 KB raw at worst (31 days × ~400 chars of reason), about 3 KB gzipped; `person()` +1 KB for the 30-day default, ~15 KB raw for 12 months. Based on the reason sentences in `payroll_rules.py` and three short keys per day. | Budgets: API call ≤ 500 ms p95; employee screen on 3G ≤ 2.5 s p95 (`nfr-budget` §2). A few KB is well inside both. | Low. Empty keys on every day would roughly double the added bytes for nothing. | P3 · Consider | |
| OPS-5 | **No index needed.** Employee Checkin already has indexes on `employee` and on `time` (Fact, `SHOW INDEX` on local `ppj.localhost`, 12 Nov 2026). Rows read per person: **Measured** at most 54 a month on PPJ (2 punches a day, local, 12 Nov 2026); **estimate** for DTC at 4-6 punches a day: up to ~190 a month, ~2,200 for 12 months. I have no DTC copy locally, so I could not measure DTC. | No index or cache without a number that misses the budget. | None. | FYI | |
| OPS-6 | **No migrate is needed for ALV-328.** Both fields it shows, `alvoraa_rules_why` and `alvoraa_evaluated_on`, already exist on Attendance (Fact, `payroll_fields.py` 98-105). If the engineer adds any field, this row changes and a dry run is needed. The dev deploy runs migrate on every push anyway (Fact, `deploy.yml` line 159); that run is for ALV-326's new rule-set fields, and ALV-326's rehearsal covers it. | Saves a dry run that tests nothing. | None, if no field is added. | FYI | |
| OPS-7 | **No manual `bench build` and no manual `assets.json` bump on dev or production.** The image builds `alvoraa_portal` (Fact, `Dockerfile` line 313), and the deploy's `refresh_bench_files.sh` copies the assets and a new `assets.json` (Fact, line 67). The page stamps `portal.js` and `panels.css` with `?v={{ asset_version }}` (Fact, `hrms-employee.html` 47, 75), so browsers get the new files. **After a deploy, check:** the `?v=` number on `/hrms-employee` changed, and the served `portal.js` contains a new string from this slice (for example "Break not measured"). **Local only:** `docker cp` of the two files, then `touch sites/assets/assets.json` and `clear-cache` - each needs Surbhi's approval (`CLAUDE.md` §2). | `bench build` on a server takes every portal offline (`frappe-conventions.md`). A copied file without the version bump stays cached in every browser. | Without the bump locally: false "it did not work" reports. With a build on a server: every portal 404s its CSS and JS. | P1 · Recommend | |
| OPS-8 | **Rollback: revert the ALV-328 commits on `dev` and redeploy, on Surbhi's word.** No schema change and no data written, so nothing to undo in the database. Do not roll back by redeploying the previous image tag if ALV-326 shipped in the same deploy: that undoes ALV-326 too. Time: the deploy still waits up to 60 rounds for `bench version` (Fact, `deploy.yml` line 529), measured at about 7 minutes on 22 Sep 2026 (lesson 22). **I could not check** today's full deploy time, so I cannot say the rollback fits the 15-minute budget (`nfr-budget` §3). | `nfr-budget` §3: rollback ≤ 15 min. | A rollback that also removes ALV-326's pay rules mid-month. | P2 · Recommend | |
| OPS-9 | **Stop and re-check if the diff touches `deploy/nginx.conf`, any permission row or a fixture.** None is expected. The two endpoints keep their existing checks (`_subject`, `person()`'s reports-to and organisation check), so no per-tenant role listing is needed before the deploy. | One nginx serves dev and production; permission rows change who sees what. | A dev push that restarts live nginx, or a new data door. | FYI | |

### What I ran and what I quoted

- **Ran (read-only):** `git branch -r --contains HEAD`; a `SELECT COUNT` and `SHOW INDEX` on
  `tabEmployee Checkin` on local `ppj.localhost`; `wc -c` and greps on the worktree files.
- **Quoted, not run:** every deploy and bench command above.
- **Left behind:** nothing. No container, file or setting changed. This file is the only
  new file, not committed.

### FYI, not this slice

`portal.js` is 1.27 MB uncompressed and `panels.css` 227 KB (Fact, `wc -c`, 12 Nov 2026).
This slice adds a few KB. The page weight against the 3G budget is an existing question,
not one this slice should open.

### Subtract pass

Removed: a request to measure the 3G load time (no new request, a few KB added); a cache
for the allowance (one read per request is already constant); an index proposal (indexes
exist); a migration dry run (no field); a monitoring row (no new failure mode - a wrong
figure is caught by the engine-match test the brief already asks for).

---

## Re-check of OPS-6 and OPS-9 - 12 Nov 2026

**Why:** the spec (`04-functional-spec.md` §G8, US-8) now adds one HR Settings Custom Field,
`alvoraa_manager_sees_whole_line_punches` (Check, default 0), and widens the Employee Checkin
read rule in `field_app_access.py` when it is on. OPS-6 and OPS-9 above were written for "no
field, no permission change". They are superseded by the two rows below; the rows above stay
as written.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-6a | **A migrate is now needed. Ship the field the way the app ships every other HR Settings field: `create_custom_fields(..., ignore_validate=True)` inside a module `after_migrate()`, listed in both `after_migrate` and `after_install` in `hooks.py`** - not a fixture, not a patch. Fact: `home_people.after_migrate` does this for `alvoraa_birthdays_on_home`, and `field_app_settings.after_migrate` for the field-app switches; `hooks.py` has no `fixtures` entry at all (`grep -c fixtures` = 0). It lands **off on every site**: the field is new, nothing writes a value, so it reads 0. **Cheap migrate:** HR Settings is a Single (Fact, `"issingle": 1` in `hr_settings.json` on `hrlocal-bench`), so this adds one `tabCustom Field` row and **no `ALTER TABLE`** - no table lock, no copy-of-data dry run needed beyond ALV-326's. The fresh-site test (AC-28, built the way CI builds one) is the dry run for this field. Dev runs migrate on every deploy already (`deploy.yml` line 159, quoted from §3). | `after_install` matters: `provision_tenant.sh` runs `install-app`, not migrate (the comment in `hooks.py` ~719 records that this was missed once). | A new tenant without the field; the read rule's `get_single_value` still returns 0, so it fails safe, but AC-28 fails and the Desk switch is missing. | P2 · Recommend | |
| OPS-9a | **This slice now changes who can see punches, so run a read-only release check per tenant after the dev migrate, and again after the main migrate.** For each site in the stack: (1) the field exists - `SELECT COUNT(*) FROM \`tabCustom Field\` WHERE dt='HR Settings' AND fieldname='alvoraa_manager_sees_whole_line_punches'` = 1; (2) it is off - `SELECT value FROM tabSingles WHERE doctype='HR Settings' AND field='alvoraa_manager_sees_whole_line_punches'` returns no row or 0; (3) no permission row changed - `SELECT COUNT(*), MAX(modified) FROM \`tabCustom DocPerm\`` and the same for `tabUser Permission`, taken **before** and after the deploy, identical; (4) `git diff --stat origin/main -- deploy/nginx.conf` is empty. Plus one API probe on dev (`data-doors.md`): a plain manager login calls `GET /api/resource/Employee Checkin` and sees direct reports' punches only. All quoted, **for the user to approve**; I ran none on dev or production. Run via `bench --site <site> mariadb`, capturing stdout and stderr (lesson 8). | With the switch off the widened code path never runs, so behaviour at release is unchanged - but only if (2) holds on every tenant, DTC included. The widening lives in code, not in rows, so (3) proves nothing else moved. | A tenant that starts with whole-line punch access (photo and location) nobody chose - the ALV-249 shape again. | P1 · Recommend | |
| OPS-8a | **Rollback (adds to OPS-8): reverting the commits leaves a harmless orphan** - one `tabCustom Field` row on HR Settings and, if anyone ticked it, one `tabSingles` value. With the code gone nothing reads it, so access falls back to direct reports. Two catches: the tick box still shows in Desk HR Settings, doing nothing; and if it was left **on**, a later redeploy of this slice brings whole-line access back at once. Recommend: before reverting, untick it (a dev-stage data change, on Surbhi's word); deleting the Custom Field is optional tidying, not part of a rollback. | Reversibility; an orphan Check field breaks no migrate. | Confusing Desk tick box; a silent switch-on on redeploy. | P3 · Recommend | |

**Ran today (read-only):** greps in `hooks.py` and `home_people.py`; `grep issingle` on
`hr_settings.json` inside `hrlocal-bench`. **Quoted, not run:** every SQL, bench and API line
above. **Left behind:** nothing; this section is the only change, not committed.

**Subtract pass:** removed a copy-of-real-data migration rehearsal (a Single adds no column)
and a per-tenant role listing beyond the Custom DocPerm / User Permission counts (no role or
row is added).
