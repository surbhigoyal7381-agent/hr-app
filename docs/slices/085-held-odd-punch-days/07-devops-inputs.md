# 07 DevOps inputs, slice 085 (ALV-392)

## §1 Brief, first look (2026-11-19)
Read: worktree branch slice/085-held-odd-punch-days (from origin/dev fd658eff); payroll_fields.py (held fields exist: alvoraa_held, alvoraa_held_confirmed). Nothing run on any server. Production/dev state NOT checked.

| ID | Recommendation | Why | Level | Decision |
|---|---|---|---|---|
| OPS-1 | Backfill as a chunked, re-runnable script, dry-run first on a copy; commit per site, log counts per site | Grace ~166 days is small. DTC is unknown (442 staff x 18 days is up to ~8,000 rows; estimate). The 1,780-delete migrate stall shows what queued work does | P2 Recommend | |
| OPS-2 | Held marking must write the Attendance row once and never delete/re-create it; test that auto-attendance on the next 3-4 min tick leaves a held row alone | Absence-backfill trap: Frappe re-marks Absent for days it thinks are unmarked. Late machine punches (Grace hourly, DTC ~5 min) can turn odd into even after marking, so the day must release itself | P1 Recommend | |
| OPS-3 | Do not rely on "Grace Daily Draft Salary Slip Refresh" (silently dead since 18 Nov, 5 leavers roll back the batch). Fix it first, or make the release path re-save only that employee's slip | Release must change the slip. A batch that rolls back on one bad row hides every other failure | P1 Recommend | |
| OPS-4 | Keep hooks cheap: Attendance validate/on_update must do no per-row slip rebuild in the hook; one slip, one employee, on release only | Slip save is the costly part; bulk backfill with a hook per row could take minutes per site | P2 Recommend | |
| OPS-5 | Per-company limit and switch as fields on an existing settings doctype (rung: configuration/custom field), not a new DocType. Retire the Grace Server Script only after the setting is read back live | Server Script is site data, not in the repo; remove it in the same release or both rules run | P2 Recommend | |
| OPS-6 | Any new custom fields go in the existing payroll_fields.py list so migrate creates them; check a fresh CI site, not just the dev bench | Local benches hide missing setup | P2 Recommend | |
| OPS-7 | Release 00:30-06:00 IST only, on her word. Run backfill AFTER the deploy lands (prove by pin file + container + file) and migrate completes, not inside it. Avoid the 06:00 Grace slip job window | Failed or half migrate leaves later sites behind; check the job queue first | P1 Recommend | |
| OPS-8 | Rollback: redeploy previous image tag with migrations off (check the tag exists in alvoraa-app package). Backfilled held rows need a written undo (a list of ids) saved before the run | Rows have no automatic undo | P1 Recommend | |

**Run cost:** no new container, queue or volume. Extra load is one attendance check per day-end and slip saves on release only. Estimate: negligible against the NFR budget; not measured. Backfill is one-off.
**Unknowns:** DTC odd-day count, disk headroom on production, whether the scheduler lag (3-4 min) delays release. I could not check these.

Subtract pass: removed a proposed monitoring alert and a held-days report; neither is required by the brief.


## §2 Design (2026-11-19)
Read: worktree slice/085-held-odd-punch-days, 01b-ux-design.md, brief gate, `portal.js`, `hrms/hrms` in this worktree. Nothing run on any server; no browser, no measurement of the live page.

**P1 first: stock Frappe pays a "Held" row.** Fact (salary_slip.py:824): the slip's attendance query only reads statuses Absent, Half Day, On Leave. A new status "Held" is in none of them, so the slip treats it as a normal paid day. Held must be deducted by our pay engine, or the design's "Not paid until fixed" is false.

| ID | Recommendation | Why | Level | Decision |
|---|---|---|---|---|
| OPS-9 | Prove, with a slip test on a fresh CI site, that a Held day is unpaid, and that release restores pay. Add "Held" to every list below that treats Absent as unpaid | Fact: unknown status falls through. Places read: salary_slip.py:824 (LWP query), :619-664 (unmarked/half-absent days); monthly_attendance_sheet.py:28-31 (abbreviation map, Held shows blank); `payroll_slip.py:164` (not_charged = On Leave/Absent), `attendance_analytics.py:351` (counts Absent only). Not checked: salary_register, `payroll_reprocess.py`, `daily_attendance_workings`, `org_figures.py`, `home_api.py` | P1 Recommend | |
| OPS-10 | Add the option with a Property Setter on Attendance.status, created in the existing `payroll_fields.py` list (rung: configuration). No new doctype or custom field | Fact: options are `\nPresent\nAbsent\nOn Leave\nHalf Day\nWork From Home` (attendance.json:96); Frappe rejects an unlisted Select value, so every insert of Held fails on a site without it. Setter is site data, so check a fresh CI site and each tenant after migrate | P1 Recommend | |
| OPS-11 | Auto-attendance is safe by design, test it anyway | Fact (shift_type.py:380-390): "marked dates" counts any row with docstatus < 2, so a Held row is not re-marked Absent. But `mark_attendance` and employee_checkin.py:253 only know Present/Absent/Half Day; a late punch will not release a Held day by itself unless our code does it | P1 Recommend | |
| OPS-12 | No new media, no new endpoint class. Settings card and send form go through today's whitelisted routes, logged-in only | Held days and punch times are personal data: no guest route, no public file, no cache header on these responses, nothing in logs or error text. The existing `Cache-Control` for API calls stays "no store" [ASSUMPTION: not read from nginx.conf] | P2 Recommend | |
| OPS-13 | After deploy, bump `sites/assets/assets.json` in the sites volume after any `docker cp` and compare volume vs image | Fact (memory, 23 Sep, 28 Oct): the volume hides the image assets and `?v=` is one timestamp. Otherwise phones keep the old JS and show "Missing punch" | P2 Recommend | |

**Page weight / 3G.** Fact (local worktree, 19 Nov): `portal.js` is 1,274,393 bytes, 341,274 bytes gzipped. All four changed screens live in that one file, so 085 adds only strings and a few functions: estimate under 3 KB gzipped, not measured. Estimate for 3G at 0.4 to 1.6 Mbps: the file takes about 2 to 7 s on a **first, cold load**; later opens come from the browser cache. **I could not check whether this meets the 2.5 s budget**: it likely does not on a cold 3G first load, but that is an existing cost and 085 does not change it. Recommend measuring once on dev with throttling before the test with five staff. Month view and day sheet need no new request beyond today's; the live "N days will be held" count is one small call on the settings card (HR only, not on the phone path).

**Subtract pass.** Removed: a CDN, a service worker cache plan, a separate bundle split for the settings card. Nothing else.


## §3 Requirements (2026-11-19)
Read: this worktree (slice/085-held-odd-punch-days), 01b-ux-design.md incl. Design gate (D2 automatic, D5 Grace only, no DTC backfill), my §1 and §2. Memory notes on the Grace slip job and nginx/deploy traps. Nothing run on any server; no site, queue or disk state checked. Production state: **I could not check that.**

Operational requirements for the analyst to trace into user stories. OPS-1 to OPS-13 above still stand; the rows below add to them.

| ID | Requirement | Why / cost of ignoring | Level | Decision |
|---|---|---|---|---|
| OPS-14 | **Property Setter for "Held".** Created from `payroll_fields.py` so migrate makes it. After migrate, on **each tenant** (Grace, DTC, every other site, since the setter lands everywhere even though only Grace backfills), read back Attendance.status options and say the value read. A story: a fresh CI site passes an insert with status Held | Without it every Held insert fails on that site. A migrate that stopped early (1,780-delete stall) leaves later sites without it. Count sites migrated against sites that exist | P1 | |
| OPS-15 | **Backfill, Grace November only (D5).** Script lives in the repo, not typed live. Dry run first on a copy or in report-only mode: prints counts per day, per employee, nothing written. Real run in chunks (e.g. 50 days per commit), re-runnable (skips rows already Held), writes through the same code path as the daily job. No DTC run: the script must refuse any site but the named one | Estimate ~166 days at Grace (not measured). A script that can hit DTC by mistake changes pay at a live customer | P1 | |
| OPS-16 | **Undo list.** Before the real run, save the ids (name, old status, old values) of every row to be changed to a file outside the repo (`/Users/mac/hrlocal-data` locally; a server path the user names). Rollback of the data = restore from that list. Read the file back and count it against the dry-run total before starting | Rows have no automatic undo. Also take a Grace database backup first and prove it restores (priority 1) | P1 | |
| OPS-17 | **Order.** Deploy lands and is proved (pin file, container, file; all app containers one tag; assets.json volume vs image) → migrate finished on all sites → OPS-14 read back → dry run → real run → count read back. Never inside the migrate | Backfill on a half-migrated site fails on the missing status | P1 | |
| OPS-18 | **Release window** 00:30 to 06:00 IST, on her word. Finish deploy, migrate and backfill, or stop, before **05:30**. Grace's slip job runs at 06:00 [ASSUMPTION: from the memory note, schedule not re-read]; re-read the job's schedule from the site before fixing a time. Check the job queue is near empty first. Backfill must not overlap a slip refresh | Backfill and the slip job writing the same slips can clash; a deploy pause also refuses biometric posts for about a minute | P1 | |
| OPS-19 | **Stalled Grace slip refresh (dead since 18 Nov, five leavers roll back the batch).** Recommend the smaller path: do not depend on it. The release step re-saves only the affected employee's slip, one at a time, each in its own try so one bad row cannot roll back the rest, and logs failures to Error Log. Fixing the Server Script is a separate item (site data, not in the repo) and not a condition of this slice | Cheapest rung that meets the need. Fixing the batch is needed for Grace anyway, but it is a different bug. Dependency on a dead job would make Held days look unpaid on a stale slip | P1 | |
| OPS-20 | **Retire Grace's limit Server Script last.** Steps: new per-company limit saved at Grace and **read back live** (value stated) → one test day proves the new limit refuses/allows correctly → only then disable the script and read it back as disabled → test again. Disable, not delete, until the next release is proved | Both rules running double-refuses; neither running lets bad data through. The script is site data and not in git, so a delete has no undo | P2 | |
| OPS-21 | **Monitoring (no new stack).** One count only: held days per site per day, from a read-only query run by hand or by the existing scheduler into the existing log. Plus checks: Error Log entries mentioning Held or the daily job since release (count, read after the first two daily runs); `rq:workers` registration and heartbeats, not `docker ps` | A held count that jumps after release means the rule is too wide. It is a number to read, not an alert system | P2 | |
| OPS-22 | **Rollback.** Code: redeploy the previous image tag with migrations off; first confirm that tag exists in the alvoraa-app package. Allow about 7 minutes of the broken `bench version` wait (22 Sep reading, not re-measured). Data: the OPS-16 list restores the backfilled rows. The Property Setter may stay: an unused status option is harmless. Rows already Held with old code running would be paid as normal days (OPS-9), so **restore them first, or accept that**, and say so before rollback | Old code does not know Held. Rolling back with Held rows left in place silently changes pay | P1 | |
| OPS-23 | **Disk and queue gate before the pull.** Read free disk on the server and the job-queue length before the deploy; stop if disk headroom is low | A full disk broke redis and defeated restarts on 10 Sep | P2 | |

**Run cost:** unchanged from §1: no new container, volume or queue. Backfill is one-off.
**Subtract pass:** removed a proposed held-days dashboard, a scheduled alert and any DTC backfill tooling (D5). Nothing else.


## §4 Strategy (2026-11-19)
Read: worktree slice/085-held-odd-punch-days at e3918b50; `00-impact-analysis.md` and the Spec gate in `02`; my §1-3; `hooks.py` after_migrate block (lines ~651-676); `.github/workflows/ci.yml` step list; `scripts/check_*` names; `monthly_attendance_sheet.py` lines 24-104; `git diff --stat origin/dev...slice/084-employee-window` (19 files). Facts from Grace (Payroll Settings, Server Script) are the lead session's read of 19 Nov, not mine. **Nothing run on any server. Not checked: any tenant's Custom DocPerm count, job queue, disk, `nginx.conf`.**

**P1 found in the plan: D-3 is not "one line".** Fact (`monthly_attendance_sheet.py:27-36` and `:84-96`): `get_message()` builds the legend by looping over `status_map` and reading `colors[count]`. `colors` has 8 entries and `status_map` has 8. Adding `"Held": "HLD"` makes 9, so **every non-summarised sheet open raises IndexError** (inference from reading the loop; not run). That is the sheet HR prepares payroll from. If D-3 is approved it must be two lines (a ninth colour too) plus a test that opens the report with a Held row.

### Install order
| Release | Order | Gate before the next step |
|---|---|---|
| **R1 safety doors** | (1) Company User Permission for hr@grace (Q1) read back on Grace. (2) Dev deploy, prove landing three ways (pin file, container, file) and one tag on every app container. (3) Test the doors on dev: HR own row, own punch, raiser submit, no-company HR. (4) Main, night window, on her word. | No Held exists, so no data step. Nothing to backfill. |
| **R2 Held** | (1) Deploy proved. (2) Migrate finished on **all** sites; count sites migrated vs sites that exist. (3) Read back Attendance.status options and the 3 Company fields on each site (OPS-14). (4) Grace: Company values saved and read back. (5) Dry run, undo list, real run in chunks (OPS-15/16/17). (6) Hold switch on for Grace. (7) Disable Grace's limit script last, read back (OPS-20). | Switch stays **off** until the backfill count is read back. Fields ship dark, so R2 can land with no tenant affected. |

### Image and Compose
Expected change: **none** (Fact: engineer's plan adds no container, queue, volume or dependency; all new code and the vendored-sheet edit ride the existing image). Check at build: `deploy/Dockerfile`, `deploy/compose/*.yml` and `.image*.env` show no diff in the slice PR. **Pinning:** no new app or package, so nothing to pin. `check_version_pins.py` already runs in CI; it needs no change.

### Migration risk
| ID | Risk | Recommendation | Level | Decision |
|---|---|---|---|---|
| OPS-24 | Property Setter + ~10 Custom Fields all land on **every** tenant, not only Grace (DTC included). A migrate that stalls leaves later sites without "Held" (5 Nov, 1,780 queued deletes) | Before R2: read the job queue length; after: count sites migrated. Tenants without the setter must not get a Held write: the hold hook is off by default and the backfill refuses any other site | P1 Recommend | |
| OPS-25 | **Custom DocPerm trap (5 Nov).** Engineer avoids new permlevel rows (agree, D-5). Custom Fields do not add DocPerm rows, so migrate should not queue deletes; **unproven** | Add one read-only count of Custom DocPerm rows on Grace and DTC before and after the dev migrate; if it moves, stop | P2 Recommend | |
| OPS-26 | Custom Fields created only in `after_migrate` miss fresh CI and new tenants (seen in `attendance_correction.after_migrate` docstring) | Wire to both `after_migrate` and `after_install`; the CI site must pass a Held insert (OPS-14) | P1 Recommend | |
| OPS-27 | R1 changes behaviour on every live tenant (D-2: HR loses own-row and own-punch edits) with no switch | Name it in the release note and on dev with a test login; no flag (no-over-engineering) | P2 FYI | |

### CI gates
Existing and relevant: `check_app_integrity.py` (no doctype redefinition; Held is a Property Setter, fine), `check_scope_traps.py`, `check_api_paths.py`, `check_tracked_keys.py`, `check_nginx_conf.py`, `check_undefined_js.js`. **Add nothing new as a script.** Recommend as *tests in the slice*, not new gates (OPS-28, P2): a hooks pin test per new hook (hot file); fresh-site Held insert; slip test both `payroll_based_on` modes; open Monthly Attendance Sheet with a Held row; machine insert never raises. Each must be shown failing once for the right reason before it is trusted (CLAUDE.md §0.5).

### The 084 overlap
Fact: `slice/084-employee-window` is 19 files, not on dev; shares `hooks.py`, `attendance_correction.py`, `hr_api.py`, `portal.js`, `org-settings.html`, and `requests.html`. **Agree** with the engineer: R1 first (small hunks in `hooks.py` and ~5 lines at `_scope_conditions`), R2 waits for 084 on dev. Add: R1's `hooks.py` hunk is the Attendance Request `before_submit` list, which 084 also edits (`validate`). Rebase and re-read the block after 084 lands; if 084 reaches `dev` first, R1 rebases, not the reverse. **Who sequences 084 to dev is the user's call** (OPS-29, P2, open).

### Where I agree and disagree with the engineer
| Point | View | Why |
|---|---|---|
| Slip re-save inline on a machine punch | **Disagree, mildly: Recommend enqueue from day one**, `enqueue_after_commit=True`, default queue, no secret in args (ids only) | The punch is a POST from a sync tool that **halts the batch on a refusal it does not know** (engineer's own 5.4). The slip save runs `calculate_net_pay` and three year-to-date helpers: unmeasured, and held inside a request row-locked on the punch. Enqueue is one line and uses the existing worker; it is not a new moving part. Condition: confirm a worker listens on that queue (`rq:workers`, not `docker ps`), and that a failed job writes Error Log. If the engineer measures under ~2 s on the heaviest slip **and** the HR path stays inline, I withdraw this (P2) |
| Company `validate` hook, not permlevel | **Agree** | A hook works on Desk, REST and import and reads company scope; permlevel needs DocPerm rows per role per tenant, the exact thing that stalled the 5 Nov migrate. Condition: a test where an HR Manager of another company is refused through REST |
| Administrator exempt from raiser-cannot-submit | **Agree, with a guard** | `refuse_own_decision` already cannot bite Administrator, and 19 test files rely on it. Condition: record that production use of Administrator is a break-glass login and a System Manager user is **not** exempt unless the engineer says so in the code; add one test that a named System Manager raiser is refused. Not checked: whether anyone works as Administrator on tenants |
| One-line edit to vendored Monthly Attendance Sheet | **Agree it is needed, disagree it is one line** (above) | Edit is two lines and needs the legend colour. Smaller alternative if she declines the fork edit: leave blank cells and tell HR that blank = Held. Weaker: payroll is prepared from this sheet |

### Facts from Grace that change advice
- `payroll_based_on = Attendance`: the engineer's caveat (D-4) is **closed**; deducting Held in the slip hook matches Absent. `include_holidays_in_total_working_days = 1`, `consider_marked_attendance_on_holidays = 0`: the hook's skip of holiday dates must match stock's (`salary_slip.py:848-852`); test a Held day on a holiday. `consider_unmarked_attendance_as = Absent` agrees with AC-4.
- Limit script counts `docstatus != 2` and `workflow_state != Rejected` per month of `from_date`; the engineer's new count is "no `alvoraa_missing_time`" per calendar month. **Recommend one test with the same fixtures on both rules**, so the two counts agree before the script is disabled (otherwise a request is refused by one and not the other). Sales Executive exemption lives in the script; **it is not carried to the new field until HR sets the exempt-role value** (Q2): add to the OPS-20 steps.

### Rollback and checks
Code: redeploy previous tag, migrations off, confirm the tag exists in `alvoraa-app` first (OPS-22 stands). R1 rollback has no data to restore. Prove checks per OPS-17.

**Subtract pass:** I removed a proposed new CI script and a flag for the R1 behaviour change. Removed nothing else.

| Still open | Owner |
|---|---|
| OPS-24 to OPS-29 decisions (blank) | Surbhi |
| D-3 as two lines, or blank-cell fallback | Surbhi |
| Enqueue vs inline | Engineer to measure; Surbhi decides |


## §5 Release readiness (2026-11-20)
Read: worktree `.claude/worktrees/085-held-odd-punch-days`, branch slice/085-held-odd-punch-days, HEAD 208de542; base 101fd29b; `origin/dev` fetched today = 15c716f6 (12 commits past the base). Read: the diff stat and the vendored-sheet diff, `08-release-runbook.md`, `04-test-report.md`, `04b-baseline-diff.md`, `deploy.yml` (dispatch inputs, branch to tag map), the backfill script header. **Nothing run on any server, nothing pushed. Production, dev, disk, queue and job schedule: I could not check.**

**Verdict: NOT READY to push to dev. Two P1s, both fixable locally; the rest is sound.**

**P1 found today.** Fact (`git merge-tree` of HEAD against origin/dev): **085 no longer merges cleanly. Slice 084 is on dev and conflicts in `hooks.py`, `hr_api.py` and `portal.js`** (it also touches `attendance_correction.py`, `org-settings.html`; those auto-merged). Everything tested so far was tested against the old base. Rebase on origin/dev, re-read the hooks block, then re-run the 085 modules and the 084 modules together. This also lifts the "R2 waits for 084" hold: R1 and R2 now travel on one rebase, but can still ship as two releases if the user wants the doors alone first.

| ID | Item | Level | Decision |
|---|---|---|---|
| OPS-30 | Rebase on origin/dev (15c716f6), resolve the three conflicts, re-run tests and `check_app_integrity.py` after. Do not push until then | P1 | |
| OPS-31 | **Screens have no proof** (test report: ACs 8, 24-27, 29-31, 34, 37, 38 never seen in a browser). The runbook lets Surbhi test on dev, so that is acceptable, but say so: dev is where the screens are first opened | P2 FYI | |
| OPS-32 | Runbook says "give hr@grace a Company User Permission" (line 24) and the slice docs only ask the question (01c Q1). **No record that it is granted.** You told me it is; I could not check the site. Add to the runbook: "granted on <date>, row read back", and count other HR logins with no company and no Employee on DTC, aahr, PPJ, dev (runbook says not counted) | P2 | |
| OPS-33 | `portal.js` is edited by 085 and 084: after the rebase, bump `sites/assets/assets.json` in the volume and compare with the image (dev serves 27 Aug today, per memory) | P2 | |
| OPS-34 | Test debt, not a blocker: 24 full-run-only failures and ~142 setUpClass errors fail the same on the base (04b, name-set diff; one 085-only, the alv332 test, fixed in 1f83c44f). They hide any 085 regression in goals-app classes. FYI | P3 | |

### Rollout (every step needs her word; none is mine to run)
1. **Local:** OPS-30 rebase, tests green on the rebased code. Report, stop.
2. **dev** (on her word, wait for CI first, no second push while it runs). Fact (`deploy.yml`): a push to dev auto-deploys tag `dev-<sha7>` with migrate on. The automatic run uses main's copy of the workflow. Prove the landing three ways (dev pin file `.image.dev.env`, `docker top`/image tag on every app container, the file itself) and compare `assets.json`. Then: Attendance.status options include Held and the 3 Company fields exist on every dev site; Custom DocPerm count on dev before and after. Test the doors (own row, own punch, raiser cannot submit, HR with no company), then Held with the switch on at one dev tenant, a late punch releasing a day, a slip, and **opening the Monthly Attendance Sheet with a Held row** (the vendored edit).
3. **main R1 then R2**, only 00:30-05:30 IST. If the doors must ship alone, R1 needs its own cut without `held_day.py`; two releases from one rebased branch means R2 is simply the same code with the switch off. **Recommend one release, switch off everywhere** (fields ship dark), then the Grace steps. Fewer deploys is fewer 7-minute waits and fewer night windows. **Consider** two only if she wants the doors in production alone (it needs a separate R1 branch and is more work). Decision: Surbhi.

### Migration dry run on a copy (needed: yes, once)
Why: R2 adds a Property Setter and about 10 Custom Fields on **every** site; the 5 Nov migrate stalled on queued deletes (Custom DocPerm trap, unproven here). No patch file was added (`patches.txt` untouched, fact: not in the diff); the vendored sheet edit is Python only, no migrate effect.
How (local, `REHEARSAL.md` route): restore the latest Grace and DTC backups into a throwaway stack, record job-queue length and Custom DocPerm count, run `bench --site <copy> migrate`, record both again, then read the Attendance.status options and the 3 Company fields, and run the backfill dry run against the Grace copy. Stop if either number moves. Not run by me.

### Deploy commands — FOR SURBHI TO APPROVE (quoted, not run)
- Dev: `git push origin slice/085-held-odd-punch-days:dev` after OPS-30. **FOR SURBHI TO APPROVE.**
- Main: `git push origin <exact sha>:main` in the window. **FOR SURBHI TO APPROVE.** The workflow maps branch main to tag `prod-<sha7>` and migrates.
- If the automatic run needs a hand: `gh workflow run Deploy --ref dev -f environment=dev -f image_tag=dev-<sha7> -f run_migrations=true`. **FOR SURBHI TO APPROVE.**
- Rollback deploy: `gh workflow run Deploy --ref main -f environment=production -f image_tag=<previous prod tag> -f image_package=alvoraa-app -f run_migrations=false`. **FOR SURBHI TO APPROVE.** First confirm the tag is in the `alvoraa-app` package.
- Backfill (Grace, after steps 1-7 of runbook §2): dry run, then `--apply`, then `--undo`, exactly as the script header gives them, from the bench folder with `env/bin/python`, undo file outside the repo. **Each one FOR SURBHI TO APPROVE separately.** Do not `docker cp`, do not pipe it into `bench console`. The script refuses any site but grace.alvoraa.co and any day outside 1-30 Nov (header, read; not run).

### Post-deploy checks, per tenant (read the value, write it down)
- **All sites:** sites migrated = sites that exist; one image tag on every app container; Held in the status options; 3 Company fields; hold switch **off** (fields ship dark); Custom DocPerm count unchanged; a normal punch and a machine punch still save.
- **DTC (switch stays off, no backfill, D5):** count of Held rows = 0 after a day; Monthly Attendance Sheet opens; biometric posts accepted after the deploy pause (about 1 min refused); HR login with a company still approves a colleague's correction.
- **Grace:** runbook §2 steps 3-9 in order; limit 3 and exempt `Sales Executive` read back; test day before the Server Script is disabled and again after; switch on, card count written down; dry-run count agrees; Held count for November equals the count printed; undo file copied off the server; hr@grace sees the team.

### Rollback (project rule: revert only)
Matches runbook §4 and I agree with it. Order: **undo list first** (`--undo`, same file), **then** the previous image tag with migrations off. Old code pays Held rows as normal days, so reversing the order silently changes pay. Property Setter and fields may stay. Days held after the backfill have no undo list. Real time is about 7 minutes (22 Sep reading, not re-measured). Revert by a new commit on main, never a force push.

### Monitoring (no new stack)
Error Log count mentioning Held after the first two daily runs; held-day count per site per day read by hand; `rq:workers` registration and heartbeat, plus `docker top`, not `docker ps` alone. Slip refresh job runs on queue `short` (impl notes): confirm a worker listens on it. Cache headers on the month call: nginx adds none (read), Frappe's own not proved, open the network tab on dev.

### Traps checked against the plan
nginx: the diff touches no `deploy/` file (fact, stat shows none), so `nginx -t` is not triggered; if that changes, run `scripts/check_nginx_parses.sh` first. Queue/disk gate before the pull (OPS-23, in runbook §0). Window 00:30-05:30 IST and Grace's 06:00 job: schedule still to be read from the site. Grace November backfill is a separate approved step, after the switch and the dry-run agreement.

**Still open:** OPS-30 (P1, blocks push), OPS-32, OPS-33, one-vs-two releases, OPS-29 now answered by events (084 is on dev). Earlier OPS-24 to OPS-28 decisions remain blank.
**Subtract pass:** removed a proposed two-branch plan from the default recommendation and a proposed new CI gate for the sheet (the slice test covers it). Nothing else.

## 6 · Rollout update, 20 Nov 2026 (coordinator, from Surbhi's decisions)
**One release, not two.** Rollout item 3 above ("main R1 then R2") is replaced: ONE push of the whole slice to main in the night window, hold switch OFF for every company (the field default is 0, test-pinned), then switched ON for Grace only by the runbook steps. A separate Release 1 cut without `held_day.py` is no longer needed, so OPS-32 and the one-vs-two question are closed. New per-tenant precondition: HR logins with no company get one first (they now also lose punch edits and approvals), and sync accounts get Company User Permission rows to be scoped (runbook, last section).

## §7 Release readiness re-check after the fix round (2026-11-20)
Read: worktree `.claude/worktrees/085-held-odd-punch-days`, branch slice/085-held-odd-punch-days, HEAD 148cb639; `git fetch origin dev` run today; `08-release-runbook.md` (80 lines); `field_app_access.py` lines 54-77 and 265-345 (R2/R4). Nothing run on any server, nothing pushed. Tenant state, disk, queue and schedules: **I could not check them.** This section replaces the HEAD and the "084 conflicts" line of §5 (HEAD was 208de542 then).

**Verdict: READY to push to dev on the code and plan, with three runbook gaps (OPS-35 to OPS-37) that must be fixed before MAIN, not before dev.** Fact: nothing in the plan blocks a dev push.

**Dev moved again.** Fact: `origin/dev` = acc89592 (today). HEAD already contains 15c716f6; dev is **two commits ahead** of it: f5b84441 (084 test report, reviews, release readiness; docs only) and acc89592 (`scripts/check_positions_tree.js`, 22 new lines; a CI check script). Fact: `git merge-tree --write-tree HEAD origin/dev` exit 0, no conflict list: a fresh rebase is clean. Neither commit touches `hooks.py`, `hr_api.py`, `portal.js` or any file 085 edits (diff names read). **Recommend:** rebase once more just before the push (fetch again; dev moves) and re-run `check_app_integrity.py`; no need to re-run the 085 test modules for these two commits (docs and one JS check script), but `check_positions_tree.js` runs in CI, so wait for CI.

Fit of the runbook to ONE release: sections 1 and 2 read as two checklists in one release (correct), `§0` gates, rollback order (undo list, then old image) and the read-through list are consistent with §6 above. Two stale phrases to tidy (P4): "Before Release 2" (runbook §5) and "After Release 1" (first checklist) should say "before the push" / "after the release".

| ID | Recommendation | Why / cost of ignoring | Level | Decision |
|---|---|---|---|---|
| OPS-35 | **Runbook: add the read-back queries for the sync accounts' Company User Permission rows, per tenant** (below). Count rows per account, not just "some exist". File one test punch per account afterwards | Fact (`field_app_access.py:279`): an account with no rows stays unscoped, so R2 does nothing until the rows exist, silently. Inference: a row for the wrong company refuses every punch that account files and repeats the 2 Nov outage (ALV-302) for that machine, with only an R2 line in the security log, which ALV-391 says may not be written | P1 for DTC (8 machines), P2 for Grace | |
| OPS-36 | **Runbook: replace "count HR logins without a company, not checked" with the query below, and write the counts per tenant before the push.** The 5 tenants named (dev, DTC, Grace, aahr, PPJ) are the ones I could see named; the real list is whatever `bench --site all list-apps` / the sites volume shows | Fact (R4 code): a human HR login with neither a Company User Permission nor an Employee company is refused every punch change and approval (the M-2 lock-out, on purpose). Cost of ignoring: HR cannot correct punches the morning after | P1 | |
| OPS-37 | **Runbook: hr@grace is a read-back, not a grant.** Replace "Give ... hr@grace" with "granted 20 Nov 2026 (per Surbhi, this session); read the row back before the push and write the value". Add the dry-run block (below). | I could not read Grace's site, so the grant is **unverified by me**. A row granted for the wrong company, or later removed, locks HR out | P2 | |
| OPS-33 | (unchanged, now concrete) after the rebase `portal.js` differs from the volume's: compare `sites/assets/assets.json` in the sites volume against the image's, and bump it after any `docker cp` | Memory 23 Sep, 28 Oct: volume hides image assets | P2 | |
| OPS-38 | **Migration dry run on copies: needed, once, before main.** Runbook has no such step (read: no "dry run" of a migrate; its "dry run" is the backfill's). Add it | Property Setter + about 10 Custom Fields land on every site; 5 Nov stall | P1 for main | |

### Read-back queries (read-only; run by the user or with her word; **I have not run any of them**)
Run per tenant, from the bench folder, as `env/bin/python`-based `frappe.init`/`frappe.db.sql` or `bench --site <site> mariadb`. Not piped into `bench console` (memory 13 Nov: piped scripts lose lines).

**A. Sync accounts, and the rows that scope them (R2).** Which accounts are machines (the sync role, no Employee record), and how many Company rows each has:
```
select r.parent as account, count(p.name) as company_rows, group_concat(p.for_value) as companies
from `tabHas Role` r
left join `tabUser Permission` p on p.user = r.parent and p.allow = 'Company'
where r.parenttype = 'User' and r.role = 'Biometric Sync'
  and not exists (select 1 from `tabEmployee` e where e.user_id = r.parent)
group by r.parent;
```
Expect: **company_rows >= 1 for every account**, and `companies` equals exactly the companies whose staff that machine punches for. A 0 means R2 is not on for that account. **DTC:** the count of accounts returned should match what was set up (8 machines may share one account, `biometric.sync@dtc`, as the code comment says; I do not know; read the count rather than assume 8 rows). **Grace:** expect `biometric.sync@grace.alvoraa.co` with Grace's company; the two machines GRCDARIA1 and GRCSECU1 post through that one account (Unknown: I read that in the brief, not on the site). A user permission row's `applicable_for`/`apply_to_all_doctypes` is not read by R2 (fact, line 279 filters user + allow only). **Recommend the narrow pattern** (one row per doctype that needs it, no `apply_to_all_doctypes`) as on DTC (memory 26 Oct), so the row does not also restrict what the account reads elsewhere. After adding: file one test punch per account for an employee of its company, read that it saved, and read the security log for an R2 line only when a punch for another company is tried (test on dev first; on production only with her word).

**B. Human HR logins with no company (M-2 lock-out count).** Excludes machine accounts (they go through R2, not R4):
```
select u.name
from `tabUser` u
join `tabHas Role` r on r.parent = u.name and r.parenttype = 'User' and r.role in ('HR Manager','HR User')
where u.enabled = 1 and u.name <> 'Administrator'
  and not exists (select 1 from `tabHas Role` s where s.parent = u.name and s.role = 'Biometric Sync')
  and not exists (select 1 from `tabEmployee` e where e.user_id = u.name and ifnull(e.company,'') <> '')
  and not exists (select 1 from `tabUser Permission` p where p.user = u.name and p.allow = 'Company')
group by u.name;
```
Expect **0 rows after the fix**; write the count per tenant before the push. Each name returned needs a Company User Permission first. Administrator is excluded (exempt by design). System Manager users without an HR role are not in this list because the R4 branch needs `is_hr`; not checked in code beyond line 296-297.

**C. hr@grace (read-back of the grant).**
```
select user, allow, for_value, applicable_for, apply_to_all_doctypes
from `tabUser Permission` where user = 'hr@grace.alvoraa.co' and allow = 'Company';
```
Expect one row, `for_value` = Grace's company name as the Company record spells it. Write the value read. Then, logged in as hr@grace on dev-equivalent or after release on Grace, the team shows on the month view.

### Migration dry run on copies (add to runbook §0)
**For the user to approve; not run.** Local only, `REHEARSAL.md` route, in a throwaway stack: restore the latest Grace and DTC backups; record `select count(*) from `tabCustom DocPerm`` and the job-queue length; `bench --site <copy> migrate`; record both again; read Attendance.status options include Held and the three Company fields exist; read the hold switch is 0 for every company; run the backfill dry run (default) against the Grace copy. **Stop if the DocPerm count or the queue moves.** Then remove the throwaway stack and say so. A backup you have not restored is not a rehearsal: say which backup file and its date.

### Still open
OPS-35, 36, 37, 38 (runbook edits are the engineer's file; I did not edit `08`). Earlier OPS-24 to OPS-28 decisions still blank. Unknown: every tenant's counts, disk, queue, the 06:00 Grace job schedule.
**Subtract pass:** removed a proposed per-machine row check by device id (the account is the unit, and the code never judges by device) and a proposed security-log alert; kept only the three read-only queries. Nothing else.
