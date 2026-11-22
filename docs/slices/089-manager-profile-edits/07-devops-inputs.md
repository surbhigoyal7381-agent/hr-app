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
