# 089 manager profile edits: DevOps inputs

## §1 Brief (22 Nov 2026)

Read: worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, SHA c9d702f0 (origin/dev). Code only. No site, container or server was touched. Risk tier (usage-discipline.md): **1** (who can change what, personal data, a leaver's pay effects).

### Red flags (bad news first)

- **P1 candidate: "Set to Left" has side effects I could not fully list from this repo.** Proven: our hooks on Employee `on_update` include `block_devices_for_leaver` (stops field phones, writes device rows), `manager_scope.on_employee_update`, `own_record_permission.on_employee_update`, cache invalidation (`alvoraa_portal/hooks.py` ~l.305). HRMS `on_update` runs `update_approver_role`, `publish_update` (`hrms/hrms/hooks.py` ~l.254). Not checked: ERPNext's own Employee code (user disable, reports-to checks) is not in this repo; I have not read it. Needs a read plus a dry run on a copy.
- **Red flag: every Employee save by Payroll team fires all those hooks.** The confirm step must go through `doc.save()` as the brief says, but one hook failure blocks the confirmation. Dry run must include an employee with a field phone, a login, direct reports and open leave.
- **Red flag: the Employee being set to Left may have direct reports.** Not checked what Frappe does with their Reports To. Decide before build.
- **Red flag: "Payroll team" role not found in this repo** (grep of py/json/md returned nothing; it is a DTC site role). Inferred: it may not exist on other tenants (Grace, PPJ, new tenants). Then a notice has nobody to confirm it. Ask: what happens on a tenant without that role?
- Not checked: whether a mid-month Left date interacts with held or draft salary slips (the 18 Nov Grace note says five leavers once rolled back a whole daily draft-slip batch, silently). Dry run should include a leaver and then the nightly job.

### What this adds to run

| Item | Verdict | Basis |
|---|---|---|
| New DocType for the leaver notice | **Recommend none if possible.** Cheapest rung: a ToDo or a Comment/field on Employee already assigned to the Payroll team role. A new DocType is a table, permissions, migrate and retention to carry (leaver notice holds personal data; counsel's clocks apply). Say which rung the BA/engineer pick. | inferred; not decided |
| Queue job | None needed. Do the write in the request. | inferred |
| Notification to Payroll team | Optional. If used, one in-app/email per notice. Email is muted on production until DTC go-live is settled; check the queue before unmuting. | memory: Brevo note |
| Scheduled job | None. Do not add a reminder job unless asked. | inferred |
| Admin picks see/change fields in Organisation Settings | A config field on an existing single doctype. Small migrate. Reads people_fields.py (`hrms/hrms/alvoraa_org_structure/`) and my_profile.py: reuse. | proven files exist |
| nginx / public routes | **None expected.** Portal calls are whitelisted methods posted to "/" with `cmd`; no `deploy/nginx.conf` change is needed. If the engineer adds a route or upload, stop and re-ask. Website pages post to "/", so any path-based gate is blind to them (memory). | inferred |

### Run cost

**Verdict: effectively zero.** No new container, volume, job or service. One extra row write per edit and one per leaver notice. Estimate: a few hundred edits a month at 1,000 to 2,000 employees; well inside the nfr-budget. Not measured. One real cost: the profile read for a manager's reports must stay one query set, not one per report (N+1 risk) -- measure with a manager of 50 reports on a copy before saying it is fine.

### Migration risk

Low if only a settings field is added. Medium if a new DocType or a Custom DocPerm change is added (permission clean-up once stopped a DTC migrate at 1,780 queued deletes). Rule: no permission-row churn; dry run migrate on a copy per REHEARSAL.md. Add: `scripts/check_app_integrity.py` before commit; never redefine an ERPNext doctype.

### Priority change

None. It rests on 078 and ALV-266, so it should not ship alone with 078's field-rights gaps open.

### Decisions (OPS rows)

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-1 | Dry-run "set to Left" on a copy: employee with a login, a field phone, reports and open leave; then run the nightly slip job. | Side effects not fully read | A leaver blocks or half-applies | Recommend, P1 | |
| OPS-2 | Use an existing record (ToDo/field on Employee) for the notice, not a new DocType. | Smallest rung | New table to migrate and retain | Recommend | |
| OPS-3 | Confirm "Payroll team" exists on every tenant, or name a fallback role. | Not found in repo | Notices nobody can confirm | Recommend, P2 | |
| OPS-4 | No nginx or route change in this slice. | Keeps the one-nginx risk out | A dev push changes live proxy | FYI | |
| OPS-5 | Measure the manager's report list at 50 reports. | N+1 | Slow portal on 3G budget | Consider | |

Subtract pass: removed a proposed reminder job and a notification queue; nothing else removed.

## §2 Design (22 Nov 2026)

Read: worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, SHA 16c68b2f. Files only. No site, container, server or phone was touched. Tier 1.

**Bad news first: I could not measure load time on a 3G phone. Nobody has built the screens yet, so the 2.5 s figure below is an estimate, not a measurement.**

### Page weight (3G phone, nfr-budget 2.5 s)

- **Proven (counted today):** the prototype file is 35,976 bytes raw, 11,365 gzipped, with no images, no external scripts and no external stylesheets. It is a viewer page, not the product, so it is only a ceiling for the real parts.
- **Proven:** the existing Team part `templates/includes/ess/parts/team.html` is the part that will grow (size counted in this worktree; see the line in the closing note).
- **Estimate:** the report sheet, the Details personal section and the emergency-contact sheet add a few KB of gzipped HTML/JS to that part. Based on the prototype's 11 KB gzipped for all screens including the Administrator card and Desk mock-ups. At roughly 400 kbit/s effective 3G that is well under 0.1 s of extra transfer. **Inference:** the new parts do not threaten 2.5 s; the existing page and round trips decide it.
- **Round trips are the real cost.** Estimate: one POST to send a report, one to load Details, one to save an emergency contact. Each is a single call on 3G latency (about 300 to 600 ms, estimate). Keep the report send to **one call that creates the ToDo and the timeline line together**. Do not poll for the result.
- The Administrator card is desktop-only and System Manager-only: no 3G concern.

### Media

None. No image, photo upload, video or file. **Proven:** the design draws none. No volume growth, no backup growth beyond a few rows per report. If the engineer adds an attachment or an icon font, stop and ask.

### Caching (the trap)

- **Proven (ess_parts.py l.44-55):** ESS HTML parts are cached in Redis per site for 24 h, key `ess_part:<build version>:<name>`. A release changes the build version, so a new image shows new parts. Per-user data never goes in the part (it is a shared template).
- **Rule:** the part may hold only the markup. Names, dates, "Reported, not yet confirmed", the employee's top line and the Administrator's lists must come from the API call, per user. **Cost of ignoring:** one manager's "Ravi reported" text served to another person for 24 h.
- **Risk to check at release (not checked):** after `docker cp` onto a running dev site the part will show the OLD text until the build version changes or the key is cleared. Needs `bench clear-cache` (explicit approval, CLAUDE.md §2). A proper image deploy changes the version, so no manual step is expected. Verify on dev by reading the served part, not the deploy log.
- **Do not cache the API answers** that carry the report state, the see-list or the change-list. They must be live: a confirmed leaver must drop off at once and a removed "see" tick must hide data at once. **Inference:** if the engineer reuses an existing cached team or people call, the cache invalidation has to be added in the same change (CLAUDE.md §2 step 2). The ToDo close on Employee save is the trigger.
- The Administrator's settings change must take effect on the next request, not 24 h later. Test: tick, save, read as a manager without reloading the server.

### What must never be public

All proven against the design, all inferred for code that is not written yet:

1. The leaver report (name, date, who reported) is never on a guest or website route, never in a search sitemap, never in a public file. Whitelisted methods only, no `allow_guest`.
2. The ToDo and timeline line are visible only to the reporting manager, the confirmer and the employee. **Not checked:** Frappe's ToDo is readable by the owner and the assigned user by default, but other roles with ToDo read may see it. The security engineer should test that a colleague and a manager of another team cannot read it, through the API and the Desk list.
3. The "see" fields (personal phone, personal email, home address, emergency contact) are never put in a cached part, a log line, an error message, the notification text or the ToDo description. The ToDo carries name, date and reporter only, nothing else.
4. Secrets and personal data never travel as job arguments (none needed: no queue job in this slice).
5. No nginx or route change (OPS-4 stands). Calls post to "/" with `cmd`.
6. Logs: the refusal sentence may name the employee ID, never the phone, address or emergency contact.

### Run and release notes

- Extra ToDo rows: one per enabled holder of the role per report. At 1,000 to 2,000 employees and a few reports a month, negligible. **Estimate.** If the role has 30 holders, 30 ToDo rows per report; cap or choose a smaller role if so (one query to check on a copy).
- Retention of ToDo and timeline lines is open for counsel (design Q2). Not an infrastructure blocker; do not add a purge job.
- No new container, job, queue or volume. Nothing to add to monitoring.

### OPS rows

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-6 | Keep the ESS part markup free of per-user text; all state comes from the API, uncached. | Parts are cached 24 h in Redis per build | One person's report text shown to others | Recommend, P1 | |
| OPS-7 | One POST creates ToDo and timeline line together; no polling. | 3G round trips | Slow sheet, half-written state | Recommend, P2 | |
| OPS-8 | After deploy, read the served Team part on dev and compare with the image; do not trust the deploy log. | Redis part cache and assets volume both go stale | Old screen on a green deploy | Recommend, P2 | |
| OPS-9 | Test that a colleague, another team's manager and a guest cannot read the ToDo or the report. | ToDo default permissions not read | Leak of a leaver's name and date | Recommend, P1 (security engineer to verify) | |
| OPS-10 | Measure the Team part on a throttled 3G profile once built, against 2.5 s. | Today's figure is an estimate | Budget missed silently | Consider | |

Subtract pass: removed a proposed per-report CDN/asset review (no media) and a ToDo purge job (counsel open); nothing else removed.

## §3 Requirements (22 Nov 2026)

Read: worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, SHA 34a9347d. Files only (design `01b`, my §1-2, `alvoraa_portal/hr_api.py`, `expense_evidence.py`, `field_app_limits.py`, `REHEARSAL.md`, `DEPLOYMENT_RUNBOOK.md`). **No site, container or server was touched. I could not count role holders on any tenant** (needs a read on a site). Tier 1.

### Bad news first

- **P1: `get_employee_scorecard` is `@frappe.whitelist()` with no method limit (hr_api.py l.1151).** Proven. It answers a GET. A rate limit on a GET never fires (Frappe skips any method not listed; proven in the comment at `expense_evidence.py` l.630). So the new save and report calls must be declared POST, or the limit is decoration.
- **P2: the Scorecard answer is the leak (ALV-433).** It is a read, so it needs no limit, but it must be cut to what the Administrator ticked before release (OPS-14).

### Operational requirements (for the BA to trace into stories)

| ID | Requirement | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-11 | **No queue job, no new worker, no scheduler job.** The report writes its ToDos, the timeline line and (on confirm) the bell line inside the request. Fan-out is one ToDo per enabled holder of the confirming role. Cap it: the setting refuses a role with more than a small number of enabled holders, or the Save button shows the count (design item 8 already says so). Suggested cap 10 `[ASSUMPTION]`; the real count is **Unknown, I could not check that**. Engineer runs one count query per tenant on a copy. | A fan-out inside a request is fine at 1-10 rows. Past that, one slow tap on 3G | A 30-row write inside one tap; half-written ToDos if a hook fails | Recommend, P2. **Surbhi to confirm the cap number** | **Needs Surbhi** |
| OPS-12 | **Report and save endpoints: `methods=["POST"]` and a per-user rate limit, using the existing `_limited`/`field_app_limits` pattern.** Suggested: leaver report 10 an hour per user (a manager has a handful of reports); emergency-contact save 20 an hour per user; the settings saves (admin) none beyond System Manager. Key on the user, hashed; never on the employee ID or any personal value (the limiter writes the key into form_dict). On a limit, answer in plain words with the wait. **Also: one open report per employee**, refused if an open ToDo of this kind exists, so a double tap cannot create 2 x holders ToDos (the report is a write, so make the check and the insert in one transaction). | Stops a loop or double tap flooding holders' ToDo lists | A manager spams the confirmer; ToDo list full of duplicates | Recommend, P2 | |
| OPS-13 | **Route rules: none.** No `deploy/nginx.conf` change, no new path, no upload, no guest method. All calls are whitelisted methods posted to "/" with `cmd`. A path-based gate cannot see them (memory: website pages post to "/"), so the limit and the permission check must live in the method. If the diff touches `deploy/nginx.conf`, stop: one nginx serves production. | One-nginx trap | A dev push edits the live proxy | FYI (OPS-4 stands) | |
| OPS-14 | **Cut the Scorecard answer before release (ALV-433, and Decision 7).** Stop sending personal email, company email and gender to a manager. Send phone and address only when ticked. Test by calling the method as a manager and reading the JSON, not by looking at the screen. | The page never draws them, but the browser holds them | Personal data in every manager's network tab, on dev and main | Recommend, P1 (security engineer to verify; Surbhi decides Decision 7) | **Needs Surbhi** (D7) |
| OPS-15 | **Redis part-cache rule (from OPS-6).** The Scorecard and Team parts are cached 24 h per build in Redis (`ess_parts.py`). Markup only; names, dates, the "Reported, not yet confirmed" line and the ticked fields arrive from the live API. Add a test that renders the part for two users and asserts the strings differ nowhere. Release check: read the served part on dev, compare with the image; if a `docker cp` was used, ask Surbhi for `bench clear-cache` (explicit approval). **Do not add a cache to the Scorecard call.** | A cached "Ravi reported" shown to another person for 24 h | Leak of a leaver's name | Recommend, P1 | |
| OPS-16 | **Dry run of "set to Left" on a copy (my §1 red flag, OPS-1).** On a copy of a real tenant (REHEARSAL.md, never production), save Left with a Relieving Date for: (a) an employee with a login, a field phone, direct reports and open leave; (b) one with no login; (c) one whose Payroll-team-style role is missing. Then read: the ToDo closed, the bell line sent, `block_devices_for_leaver` ran once, reports' Reports To, the user still enabled or not, and **then run the nightly draft-slip job and check it did not roll back** (the Grace note of 18 Nov: five leavers silently rolled back a whole batch). Capture stdout and stderr; `bench execute` hides errors (lesson 8). Report the timing of the save. | ERPNext's Employee code was not read | One failing hook blocks the confirm; a leaver half-applied | Recommend, P1 | |
| OPS-17 | **Backups: no change needed, but prove the one thing that matters.** New data is a few ToDo, Comment and Version rows in the existing database; no files, no volume growth. Before the production release, the runbook's `bench --site all backup --with-files` and a size check apply as for any release (DEPLOYMENT_RUNBOOK.md). Retention for these rows is open for counsel (design Q2): **do not add a purge job**; a backup keeps them for the backup's own life, which the legal-retention clocks must account for. | Nothing new to back up | None for this slice; the retention answer is for counsel | FYI. Retention: **Needs Surbhi and counsel** | **Needs Surbhi** (retention) |
| OPS-18 | **Monitoring: watch Error Log, add nothing new.** For the first hour and the first working day after each stage, count Error Log rows (read-only) whose method or title names: the report endpoint, the emergency-contact save, `get_employee_scorecard`, the ToDo creation, the Notification Log write for the manager, and the Employee `on_update` hooks (`block_devices_for_leaver`, `manager_scope`, `own_record_permission`). Also watch: `RateLimitExceededError` counts (a spike means a loop or a wrong limit), and the confirmer's open ToDo count (a report no one confirmed for 2 working days is a person left on the payroll). The security log: refusals must appear (ALV-391 was fixed on dev; confirm it writes). The engineer adds a `frappe.log_error` on every `except` in the new calls, with the employee ID only, never phone, address or contact. | nfr-budget §8: a change you cannot see working is not finished | A failed confirm found by a payroll person weeks later | Recommend, P2 | |
| OPS-19 | **Email stays out of it.** The manager's outcome line is a bell line (Notification Log), not email. Do not send email for the report: email is muted on production and unmuting needs its own approval (Brevo note). | Keeps Brevo out of scope | An email to every holder on a muted tenant | FYI | |
| OPS-20 | **"Confirming role" missing on a tenant (my OPS-3, still open).** On a tenant where no enabled user holds the chosen role, the setting refuses (design item 5), and the report button must say so in plain words rather than create zero ToDos silently. Test with an empty role. | A report that goes to nobody | A leaver nobody confirms | Recommend, P2 | |

### Release-time commands (nothing run; for later sections)

All read-only counts and the dry run belong in §5, on a copy, for the user to approve. Nothing here is a deploy command.

### Open for you (waiting on Surbhi)

OPS-11 (fan-out cap number), OPS-14 (Decision 7, Scorecard answer cut), OPS-17 (retention of ToDo and timeline lines, with counsel).

Subtract pass: removed a proposed Redis cache for the Scorecard, a purge job for old ToDos, a new alert dashboard and an email notice; nothing else removed.

## §4 Strategy (22 Nov 2026)

Read: worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, HEAD 27eeb574 (origin/dev now 4df25095, not rebased yet). Files only: the engineer's `00-impact-analysis.md`, my §1-3, `scripts/` and `alternative_number.py` (greps). No site, container or server was touched. Tier 1.

### Where I disagree with the engineer (first)

| ID | Recommendation | Why | Cost of ignoring | Level | Decision |
|---|---|---|---|---|---|
| OPS-21 | **Drop `search_index=1` on `alv_leaver_employee`.** Keep the Custom Field. | No row count or timing is shown for `tabToDo` at any tenant, so the index is a cache-on-suspicion (no-over-engineering rule). It adds an index build on every tenant's ToDo table at migrate. Add it later only if a count on a copy shows ToDo past roughly 100k rows `[ASSUMPTION]` or a measured query misses the budget. | A table rebuild on the migrate path for no measured gain | Recommend, P3 | |
| OPS-22 | **The alv089 stack is a code test, not the migrate rehearsal.** Keep it, but do OPS-16 and the migrate timing on a copy of real data per REHEARSAL.md as a separate step. | A fresh test site has a tiny ToDo table and no leavers; it proves nothing about migrate time or Left side effects | A green local migrate read as "safe on DTC" | Recommend, P1 for main | |

### Where I agree

- **Plain ToDo insert, no `assign_to`.** Agree. Fewer side effects (no share, email, comment), no new moving part.
- **Alert-type bell.** Agree. Never emails, so OPS-19 holds.
- **Settings through `ACCESS_GRANTING`, one new file, ToDo guard, Employee hooks.** Agree: rung is "new code on existing doctypes". The Employee `on_trash` (Q4) also agrees: it stops a leaver's name staying behind in an orphan row. Two lines.
- **ALV-433 field cut.** Agree. Check it by calling the method and reading the JSON, not the screen (OPS-14).
- **Own `alv089-*` stack.** Agree, with conditions below.

### Install order, image, Compose

1. Rebase on origin/dev first (two portal.js commits, other regions; engineer has read them).
2. Order inside one release: code lands, then `bench migrate` creates the Custom Field via `after_migrate`/`after_install` (same way as slice 080's `create_custom_fields`, which writes only what is missing, proven in `alternative_number.py`), then the app restarts. Code that reads `alv_leaver_employee` before migrate would fail on that query: the guard and the ToDo query must treat a missing column as an error logged once, not a crash of Employee saves (the engineer already wraps the Employee hook).
3. **Image and Compose: no change.** No new app, dependency, container, volume, queue, scheduler job or nginx file. Check the diff has none of `deploy/compose/*`, `Dockerfile`, apps list, `deploy/nginx.conf`.
4. **Version pinning: nothing to pin.** The engineer read Frappe 16.33.1; dev and production running the same version is **not checked**. The `ToDo`, `assign_to` and Notification Log behaviour the plan leans on is version-specific, so the check belongs in §5.

### Migration risk

- **Low, not zero.** One Custom Field, no `Custom DocPerm` change, so the 5 Nov failure (1,780 queued deletes stopping the DTC migrate) does not apply by cause. Inference: adding a column to a small table is quick. Not measured; MariaDB version and `tabToDo` row counts per tenant are **not checked**.
- Still apply the standing rule before main: read the job queue length before the migrate, and after it count the sites that finished against the sites that exist (scope words are claims).
- `after_migrate` runs on every tenant on every migrate. It is safe because it writes only what is missing; a test should run migrate twice and show one field.
- One more `doc_events` handler on every Employee save and every ToDo save. Cost is near zero (first line returns unless status became Left). The dry run (OPS-16) is what proves it.

### CI gates to add (all small, none new tools)

| ID | Recommendation | Why | Level | Decision |
|---|---|---|---|---|
| OPS-23 | `python scripts/check_app_integrity.py` before commit (lesson 7). No Frappe or ERPNext doctype redefined; the Custom Field is on ToDo, not a stub. | Standing rule | Recommend, P2 | |
| OPS-24 | Raise the `ignore_permissions` ceiling test deliberately, by the counted 2 in `leaver_report.py`, with the reason in the test. I found no ceiling script in `scripts/`; the engineer names `test_portal_security_010` for `hr_api.py`. Confirm which test also covers new files. | A ceiling that is quietly raised is no gate | Recommend, P2 | |
| OPS-25 | Hook pin test: all three `ToDo.validate` handlers still run, and it names 089. Register the new DOM test in `scripts/run_dom_tests.js`. | Hot-file merge safety | Recommend, P2 | |
| OPS-26 | Break tests (engineer's four) committed first, each shown failing then restored. | A gate that cannot fail | Recommend, P1 | |

No nginx gate (`check_nginx_parses.sh`) is needed because nginx is untouched. If the diff touches it, stop.

### The local test stack

- **Disk first (lesson 16):** read free disk and `docker stats` before starting a sixth stack (about 975 MB each, from `parallel-work.md`). Stop it when finished.
- **Image gap:** the stack uses image `dev-3830ed3` with the three apps bind-mounted from this worktree. Bind-mounted code does not bring new pip dependencies or built assets. 089 adds none, but the base is older than origin/dev, so say the image tag in every test report.
- **Fresh site built the way CI builds one (lesson 6).** The engineer says how `alv396` was seeded is not checked. Do not copy that unknown; build `test_site` as CI does, so a missing setup step shows here.
- Run `bench migrate` on this stack twice (idempotence), capture stdout and stderr (lesson 8). It touches only `alv089-*`. Needs Surbhi's yes (Q6).
- Restart the stack's bench after any site switch (lesson 12).

### Leftover risk to name

Release time still owes: per-tenant counts of ToDo `Custom DocPerm`, `Notification` and `Assignment Rule` rows on ToDo (the engineer's list), role-holder counts for the cap, and the Redis part-cache read on dev (OPS-8/15). All on a copy or by read, with Surbhi's approval. Nothing here is a deploy command; those come in §5.

Subtract pass: removed the search index (OPS-21) from the plan; added no new check beyond what the engineer already listed. Left behind: nothing created; only this file edited.
