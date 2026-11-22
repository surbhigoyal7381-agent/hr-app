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
