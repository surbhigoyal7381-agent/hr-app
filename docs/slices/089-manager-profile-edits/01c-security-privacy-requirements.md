---
slice: 089-manager-profile-edits
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-22
status: draft, for the business analyst and Surbhi
risk tier: 1 (who can see and change what, personal data, a date that stops pay)
inputs: 01-product-brief.md, 01b-ux-design.md (both with Surbhi's gate decisions), prototype-v4.html, 07-devops-inputs.md §1-2, security-compliance-baseline.md
---

# 089 · Security and privacy requirements

**What I read.** Worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, HEAD `34a9347d`. Frappe and ERPNext source: read only, inside the shared `hrlocal-bench` container (Frappe `16.33.1`, commit `988e54f`, 8 Sep 2026). **That bench may not run the same Frappe as dev or production.** I did not check. No site was opened, no login was used, nothing was run against data. No server was touched.

**Labels.** **Proven** = I read the line named. **Inferred** = my reasoning from what I read. **Not checked** = I did not look.

**Builder and reviewer.** I wrote these requirements. At review (`06`) I will be checking my own requirements, so a second reader should check the rows marked ⚠ (lesson 6).

## Bad news first

1. **The Frappe ToDo and the timeline line belong to the manager who sends the report, so that manager can change or delete them.** Proven: Frappe sets `owner` to the signed-in user on every insert (`frappe/model/document.py` about line 808, outside install, patch and migrate). ToDo gives role `All` write and delete (`todo.json`), and `todo.has_permission` lets the owner in. `frappe.desk.form.utils.update_comment` (whitelisted) lets a comment's owner rewrite it. So without a guard, a manager could change "last working day 30 Nov" to any other date, or delete the notice. SEC-9 closes this.
2. **Assigning a ToDo can quietly share the whole Employee record.** Proven: `frappe/desk/form/assign_to.py` `_add`: if the person given the ToDo cannot read the Employee, Frappe adds a DocShare for them, unless document sharing is switched off. With a role-wide ToDo, an HR Manager of another company would get read access to this employee's record. SEC-7 forbids it.
3. **A second reader leaks the same fields as ALV-433, and it draws them.** Proven: `hr_api.get_employee_detail_for_manager` (line 1491) sends `cell_number`, `personal_email`, `company_email` and `gender`. `renderEmpDrawer` in `portal.js` draws the phone, company email and personal email. Inferred: no screen opens it today (`openEmpDrawer` has no caller in the repo), but the method is still whitelisted, so any direct manager can call it. SEC-1 covers both readers.
4. **`MANAGER_EDITABLE` is the wrong place for the exception.** Proven: `employee_has_permission` (`employee_field_rights.py` line 307) does not check the reporting line, the Administrator's ticks, or the person's status. It only checks which fields changed. Inferred from the `own_record_permission.py` docstring, not tested: a manager can reach every person below them in the tree, not just direct reports. So putting a field in `MANAGER_EDITABLE` would let a skip-level manager change it through the REST API, whatever the Administrator ticked. SEC-4 keeps it empty.
5. **If the new settings are not added to `ACCESS_GRANTING`, an HR Manager can change them and no Version row is written.** Proven: `settings.set_cover_setting` (`hrms/hrms/alvoraa_org_structure/settings.py` line 428) only sends keys in `ACCESS_GRANTING` down the System-Manager-only path. Every other key falls through to `frappe.only_for(["HR Manager", "System Manager"])` and a plain `set_default`. SEC-3.

## 1 · Threat model in four lines

1. **Who wants it, and the cheapest way.** A manager who wants a report's home address, or wants someone gone. Cheapest: call the whitelisted method directly for someone who is not their direct report, or send a false or repeated leaver report. The second group is an HR person of one company who gets a ToDo for another company's employee.
2. **Blast radius of one mistake.** The address and phone of one manager's team. One person's pay stopped early if a false report is confirmed. If recipients or shares are wrong: **cross-company**, which is the top of the scale.
3. **What becomes possible that was not.** A manager writes to someone else's record (emergency contact). A manager writes a statement about a person (the leaver report) that reaches HR. A manager can see home address and personal phone.
4. **How we find out.** A refusal goes to `security.log`, but only where the ALV-391 fix is deployed. Each change writes a Version row. Each report leaves a ToDo and a timeline line. **A manager reading an address leaves no trace at all.** That is a residual risk (§9), not a requirement.

## 2 · Data inventory

| Data | Class | Purpose | Kept | Who may see it |
|---|---|---|---|---|
| `cell_number` (personal phone) | personal contact | reach a team member | as the Employee record | the person, HR, a direct manager **only if ticked** |
| `current_address` (home address) | personal contact | as above | as the Employee record | as above |
| `person_to_be_contacted`, `relation`, `emergency_phone_number` | personal contact (also a third person's data) | emergencies at work | as the Employee record | as above; a direct manager may change them **only if ticked in "change"** |
| `personal_email`, `permanent_address` | personal contact | none in this slice | – | **never sent to a manager** |
| `company_email`, `gender` | work contact / personal | none on the Scorecard | – | **not sent by the Scorecard** (nothing draws them) |
| Leaver report: person, last working day, reporter, date sent | employment, affects pay | tell the confirmer | **open, for counsel (PRIV-4)** | reporter, confirmers who may read that employee, the person reported; see SEC-10 for the full list |
| Outcome bell line | employment | tell the reporter | Notification Log's own setting (not checked) | the reporter only |
| Version row for an emergency-contact change | audit | answer "who changed it" | Version rows are not cleared by Log Settings (proven: `settings.py` docstring, line 445) | System Manager |

## 3 · Access intent, including who must NOT see what

| Who | Personal details card | Change emergency contact | Send a leaver report | ToDo / timeline line |
|---|---|---|---|---|
| Direct manager (`reports_to` = own **Active** Employee) of an **Active** person | ticked fields only | if ticked | yes | sees their own report |
| Skip-level manager | **no** | **no** | **no** | timeline: see ⚠ Q1 |
| HR-covered person (no `reports_to`; `get_effective_manager` falls back to the HR Manager employee, proven `alvoraa_goals/permissions.py` line 64) | via HR's own rights, not as "manager" | no | **no** | – |
| Colleague, another team's manager | **no** | **no** | **no** | **no** |
| HR of another company | **no** | **no** | – | **no**; no ToDo, no share |
| Confirmer (holds the set role, can write status, covers the company) | – | – | – | yes |
| The person reported | – | – | – | sees the open-report line about themselves |
| Manager of a person who has Left | **no** | **no** | **no** | – |
| Guest | nothing | nothing | nothing | nothing |

## 4 · Obligations engaged

| Obligation | Source and date checked | What it asks of this slice |
|---|---|---|
| DPDP Act 2023, reasonable security safeguards; most Rules commence **14 May 2027** (one source says 13 May) | Amss Shardul note, read 22 Nov 2026; baseline §2 verified 24 Aug 2026, **90 days old today, refreshed here** | access control and logging on the new paths (SEC-1 to SEC-12) |
| DPDP Rules 2025: keep personal data, traffic data and processing logs **"for at least one year from the date of such processing"**, for the Seventh Schedule purposes | Amss Shardul note, read 22 Nov 2026. **Secondary source; I could not read the Gazette PDF** | a floor for PRIV-4. ⚠ Counsel: does it apply to a leaver notice? |
| DPDP: purpose limitation and data minimisation | baseline §2, 24 Aug 2026 | PRIV-1 |
| DPDP: notice | baseline §2, 24 Aug 2026 | PRIV-2 ⚠ |
| Counsel, 18 Sep 2026: performance records kept for employment + 6 months. Counsel, 21 Nov 2026: attendance and pay kept 5 years | memory notes, as Surbhi reported them; **not counsel's written words** | the nearest rulings for PRIV-4; neither covers a leaver notice |

I am not a lawyer. Every ⚠ row needs counsel or Surbhi.

## 5 · Abuse cases

| Case | What stops it | Requirement |
|---|---|---|
| Manager reports someone who is not their direct report (skip-level, other team, HR-covered, another company) | the server checks `reports_to` against the caller's own Active Employee. Not `get_effective_manager`, and not tree reach | SEC-6 |
| Manager reports themselves | refused by name | SEC-6 |
| False report, in anger | nothing changes until a confirmer saves Left; the person sees the open report; no free text is collected | SEC-6, PRIV-2, PRIV-3 |
| Repeated reports to pressure HR | one open report per person; a per-manager rate limit (reuse `field_app_limits._limited`) | SEC-6 |
| Reporter rewrites the date after sending, or deletes the notice | ToDo and comment guards | SEC-9 |
| Manager who is also HR reports, then confirms alone | reporter is never a recipient. They can still save Left in Desk, as they can today | SEC-7, §9 |
| An HR Manager is reported and receives their own ToDo | the person reported is never a recipient. `refuse_own_locked_change` already stops them saving their own status (proven, line 203) | SEC-7 |
| Administrator picks "Employee" as the confirming role: every staff login gets a ToDo and a share | the setting refuses broad roles and roles with no eligible holder | SEC-8 |
| Manager harvests home addresses through the API for people who are not theirs | direct-report check on the reader; refusal logged | SEC-2, SEC-5 |
| A departing manager with a valid session | `_get_employee` filters `status = "Active"` (proven, `hr_api.py` line 307), so a Left manager is no one's manager | SEC-2, SEC-6 |
| Manager keeps reading a leaver's address after they left | personal details only for an Active person | SEC-2 |
| Forged POST from another page | CSRF check, proven to run | SEC-12 |

## 6 · Requirements

Each one says what must be true and how it is tested. The analyst traces every one to an acceptance criterion. "Plain manager" means a login with Employee / Employee Self Service and no HR role, tested **on the test site, as that login, through `/api/method/...`**, not by calling the Python directly.

### Security

**SEC-1 · ALV-433: the Scorecard sends only what it draws (P1).**
`get_employee_scorecard` and `get_employee_detail_for_manager` no longer return `personal_email`, `company_email` or `gender` to anyone. They return `cell_number`, `current_address` and the three emergency-contact fields only when SEC-2 allows it. Smallest fix: drop the fields from the `frappe.db.get_value` list (lines 1169-1175 and 1507-1513) and add the ticked ones, from one helper used by both readers. The drawer then shows "No contact info", or is removed. That is the engineer's choice. The fields must not stay on the wire.
*Test:* as a plain manager with both lists empty, call both methods for a direct report. Assert that none of the 8 keys appear anywhere in the JSON. Tick personal phone, call again with no server restart: only `cell_number` appears. Untick: it is gone on the next call (no cache, DevOps OPS-6). `personal_email` never appears in any state.

**SEC-2 · Who gets the personal details card.**
Personal fields go to a non-HR caller only when all four are true: (a) the person's `reports_to` equals the caller's own **Active** Employee (`_get_employee`); (b) the person is **Active**; (c) the field is ticked in "Managers can see"; (d) the field is on the closed list in PRIV-1. The `get_effective_manager` fallback (the HR Manager employee for people with no manager) does not count as "manager" here. HR callers keep their existing company scope (`_hr_target_employee`).
*Test:* a matrix of callers: direct manager, skip-level manager, colleague, another team's manager, manager of a Left person, Left manager, HR of the same company, HR of another company. Assert who gets the fields. A refused caller gets the SEC-5 log line. The matrix must also hold one **allowed** case, so the test cannot pass because nobody is allowed (an empty result is not a finding).

**SEC-3 · The three new settings are access-granting.**
The keys for "Managers can see", "Managers can change" and "Leaver notices are confirmed by" are added to `ACCESS_GRANTING` in `settings.py` and saved only through `set_cover_setting`. The save refuses: any field outside the closed lists in PRIV-1; any "change" field not also in "see"; any value for `personal_email`, `permanent_address` or anything on `people_fields.NEVER`.
*Test:* an HR Manager's save is refused, logged, and writes nothing. A System Manager's save writes one Version row with the old and new value. A save that puts `personal_email` in "see", or `cell_number` in "change", is refused with a sentence. Nothing is written.

**SEC-4 · The narrow exception to ALV-266 lives in one endpoint, not in `MANAGER_EDITABLE`.**
`MANAGER_EDITABLE` stays `()`. The manager's emergency-contact save is one whitelisted method, `methods=["POST"]`, with the same shape as `my_profile.save_my_profile`. It takes the person's ID and the three fields. It refuses (never drops) any other key. It applies SEC-2 (a), (b) and the "change" tick. It writes one Version row per save, owned by the manager, with old and new values. It writes no log line with a value in it. It is rate limited per user with `_limited`. Why not `MANAGER_EDITABLE`: proven, that hook checks no reporting line, no tick and no status, and it would open the REST door to every user who can reach the record.
*Test:* (1) assert `MANAGER_EDITABLE == ()`. (2) A direct manager's save with "change" ticked works, and the Version row names the manager. (3) Refused and logged in each case: unticked, skip-level manager, Left person, extra key `cell_number`, the caller's own record. (4) As that manager, `frappe.client.set_value("Employee", report, "emergency_phone_number", ...)` is still refused by ALV-266. (5) Break-test: comment out the `reports_to` check and watch test 3's skip-level case fail. Then restore it.

**SEC-5 · Every refusal on these paths is logged, and the log is real.**
Every refusal in the new endpoints goes through `hrms.alvoraa_hr_core.access.refuse` with a rule ID. So do the two existing `frappe.throw("Access denied", ...)` lines in `get_employee_scorecard` (line 1163) and `get_employee_detail_for_manager` (line 1503). Today those two leave no trace (proven). The line names the caller, the rule, the endpoint and the employee ID, and never a phone, address or emergency contact. Proven on this branch: `security_logger()` raises the logger to INFO (ALV-391). **Not checked:** whether that fix is on `main` and production. Until it is, these refusals are not observable there.
*Test:* follow the `test_security_log_alv391.py` pattern. Make a refused call, then read the line from the handler, not from a mock of `refuse`. Assert that no value from the person's record appears in it.

**SEC-6 · The leaver report endpoint.**
One whitelisted method, `methods=["POST"]`, no `allow_guest`. It refuses, with the sentences in `01b` §4.2, logged under SEC-5, when: the caller has no Active Employee; the person's `reports_to` is not the caller's Active Employee (HR-covered people included); the person is not Active; the person is the caller; a report about that person is already open; the date is before joining, more than 31 days back or more than 60 days ahead (D4, Surbhi 22 Nov 2026). The only input it takes is the date (no free text). It is rate limited per user (`_limited`). **It writes nothing to the Employee's `status` or `relieving_date`.** It writes the ToDos and the timeline line in one transaction (OPS-7).
*Test:* one case per refusal, each asserting zero new ToDo, Comment and DocShare rows. A good report: assert `status` and `relieving_date` are unchanged on the Employee. A second report on the same person is refused.

**SEC-7 · Who gets the ToDo, and no share, ever.**
Recipients are enabled users who meet all of these: (a) they hold the set role; (b) they hold one of `LEVEL_2_WRITERS`, so they can actually save Left; (c) `access.permitted_companies(user)` includes the person's company. The reporter and the person reported are left out. If nobody is left, the report is refused ("Nobody can confirm this yet. Ask HR.") and nothing is written. The report must never create a DocShare. Either do not call `assign_to.add` for a user who cannot read the Employee, or check before calling it (proven: it shares otherwise).
*Test:* two companies, an HR Manager in each. A report on a company-A employee gives a ToDo to A's HR only. The DocShare count is unchanged. A reporter who is also HR Manager gets no ToDo. A role whose only holder is the reporter: refused, nothing written.

**SEC-8 · The confirming-role setting refuses an unworkable or broad role.**
The save (SEC-3 path) refuses: `Guest`, `All`, `Administrator`, `Desk User`, `Employee`, `Employee Self Service`; and any role with no enabled user who also meets SEC-7 (b). Default `HR Manager`. The refusal uses the `01b` §4.5 sentence. **Inferred:** a role can lose its last holder after it is saved. SEC-7's "nobody left, so refuse" covers that case at send time, so no background check is needed.
*Test:* each named role refused. A role held only by disabled users is refused. A role held only by a user without an HR role is refused. `HR Manager` with one enabled holder is accepted and writes a Version row.

**SEC-9 · The reporter cannot change or remove the notice.**
After sending, the reporter cannot edit, close, reopen or delete the ToDo, and cannot edit the timeline comment. Proven door list: `frappe.client.set_value` / `save` on ToDo; `frappe.client.delete` on ToDo; `frappe.desk.form.assign_to.remove`; `frappe.desk.form.utils.update_comment`. Reuse the existing pattern of `validate` hooks on ToDo and Comment (`hooks.py` line 576-581, slice 066) plus an `on_trash` on ToDo. No new permission layer. Status changes are allowed for the confirmers and for the Employee-save auto-close only.
*Test:* as the reporter, call each of the four doors. Each is refused, and the record is unchanged. As a confirmer, closing the ToDo works.

**SEC-10 · Who can read the notice: written down and tested, not assumed.**
Proven in Frappe 16.33.1: a ToDo is readable by its `allocated_to`, `assigned_by` and `owner`, and by any role with a ToDo permission row other than the automatic ones (standard: System Manager) (`todo.py` `has_permission` and `get_permission_query_conditions`). A Notification Log is readable only by its `for_user` (`notification_log.py` line 104-117). A Comment on an Employee shows in the Desk form to anyone who can open that Employee. **Inferred:** that includes skip-level managers (tree reach, `own_record_permission.py` docstring). **Not checked:** extra Custom DocPerm rows on ToDo at DTC, Grace, PPJ or any tenant.
*Test:* with one open report, as colleague, other-team manager, skip-level manager, other-company HR and guest: `frappe.client.get_list("ToDo")`, `frappe.client.get_list("Notification Log")` and `frappe.desk.form.load.getdoc("Employee", person)`. Assert that the report's text appears for none of them, except skip-level per ⚠ Q1. One read-only query per tenant before main: list the Custom DocPerm rows on ToDo.

**SEC-11 · What the notice may say.**
The ToDo, the timeline line, the bell line and any email Frappe sends from them (proven: `notify_assignment` puts the ToDo description into the email HTML unescaped, `assign_to.py` line 285) carry only: employee name and ID, last working day, reporter's name, date sent, and the outcome. They are built on the server from record values, with `employee_name` HTML-escaped. They contain no phone, address or emergency contact, and no free text from the manager.
*Test:* create a report for an employee whose name contains `<b>x</b>`. Assert the description is escaped. Assert no field from PRIV-1's list appears in the ToDo, Comment or Notification Log rows.

**SEC-12 · The CSRF check really runs on the new POSTs.**
Lesson: `frappe/auth.py` about line 87 skips the check when the session carries no CSRF token. For the three new write methods (report, emergency contact, settings via the existing setter), prove the check fires for a portal session.
*Test:* sign in as a plain manager over HTTP, the way the portal does. POST to each method without `X-Frappe-CSRF-Token`: refused, nothing written. With the token: works. Break-test: show that the test fails if the method is made GET-able.

### Privacy

**PRIV-1 · The closed lists.**
"See" candidates: `cell_number`, `current_address`, and the emergency-contact trio. "Change" candidates: the emergency-contact trio only. `personal_email` and `permanent_address` are never offered. `[ASSUMPTION]` "Home address" means `current_address` only. That is the smaller choice; adding `permanent_address` needs Surbhi's yes. Both lists are empty on every tenant, new ones included, until a System Manager ticks.
*Test:* read the defaults on a fresh test site: both empty. The candidate list returned to the card equals exactly these fields.

**PRIV-2 · The person is told. ⚠ COMPLIANCE.**
While a report is open, the person sees the line on My profile (`01b` §4.4). After a manager changes their emergency contact, they see "Changed by your manager" (from the Version row). The method behind the line answers only for the caller's own record and returns only the reporter's name, the dates and the state. It never names the confirmers. ⚠ Surbhi or counsel: the caption "Staff can see that you can" is not a privacy notice. Does the employer's notice need a line saying managers may see a team member's phone and address, when ticked? (The baseline says the notice is the employer's; memory note of 31 Oct 2026.)
*Test:* the person reported sees the line. A colleague calling the same method gets only their own (empty) state. The response has no confirmer user IDs.

**PRIV-3 · An unconfirmed report is not a leaving fact.**
The reported date never reaches `relieving_date`, the Positions "leaving" flag (slice 059), the Team list of anyone but the reporter, a report, an export or a cached ESS part.
*Test:* after a report, `positions_profile` for that person shows no leaving sentence. A colleague's Team call shows nothing new. The served ESS part has no per-user text (OPS-6).

**PRIV-4 · How long a leaver notice is kept. ⚠ COMPLIANCE, open for counsel (Surbhi's decision 4, 22 Nov 2026).**
Until counsel answers, the fail-closed default: the notice exists only as the ToDo rows, one timeline comment and one bell line. There is no other copy: no new DocType, no export, no report, no log line with the date. No purge job is built (DevOps agrees). **Not checked:** whether erasing or deleting an Employee removes its ToDo and Comment rows. That must be read before counsel's answer can be built. **This blocks the release to main, not the build** (P1: new personal data with no retention answer).
*Test:* none until counsel answers. Then one test per rule.

## 7 · What must exist for each control to be observable (lesson 1)

- SEC-1 and SEC-2: at least one manager with a **direct report** who has a phone and an address set, and an Administrator tick. On a site where both lists are empty, "no personal fields returned" proves nothing.
- SEC-7 and SEC-10: **two companies**, with an HR Manager in each scoped by User Permission on Company. One company proves nothing about cross-company.
- SEC-5: the ALV-391 logger fix deployed. Without it, the line is never written, whatever the code says.
- SEC-9: an open report made **by the manager's own session**, not by Administrator in a test. Otherwise `owner` is wrong and the doors are never tried.
- SEC-12: a real HTTP session, not a Python call.

## 8 · Questions

| # | Priority | Question | My reading, and why it matters | Fail-closed default meanwhile | Owner | Blocks |
|---|---|---|---|---|---|---|
| Q1 | **must know** | May a skip-level manager read the timeline line "Meena reported that Ravi left" before anyone confirms? | Inferred: they can, because a Comment shows to anyone who can open the Employee, and managers reach their whole tree. The design said only reporter, confirmer and employee. | **Do not write the timeline line.** The ToDo alone carries the notice. Add the line only if Surbhi says yes. | Surbhi | SEC-6, SEC-10 |
| Q2 | should know | "Home address": `current_address` only? | Smaller is safer. | `current_address` only. | Surbhi | PRIV-1 |
| Q3 | should know ⚠ | Does the employer's privacy notice need a line on manager visibility? | PRIV-2. | Ship the caption; tell DTC in the release note. | counsel via Surbhi | main |
| Q4 | should know ⚠ | How long is a leaver notice kept? Does the DPDP Rules one-year floor apply? Is it erased with the Employee record? | PRIV-4. The nearest rulings are performance (employment + 6 months) and attendance/pay (5 years), as Surbhi reported them. | Keep it, one copy only, no purge. | counsel via Surbhi | main |
| Q5 | nice | Should a manager see a Left former report's Scorecard at all? | Inferred from code, not run: `get_effective_manager` does not check the person's status, so it opens today while `reports_to` still points at the manager. Outside this slice. | SEC-2 already hides personal fields for Left people. | Surbhi, then a ticket | nothing here |

## 9 · Worries (not findings yet)

- Q5 above: attendance, leave and appraisal history of a former report may stay open to their old manager. I could not run it.
- A confirmer can delete a ToDo, and then the record of a declined report is gone. **Not checked:** whether Frappe's Deleted Document keeps a copy.
- Assignment emails put the leaver's name and date into confirmers' mail inboxes, outside the product's retention.
- **Not checked** on any tenant: whether Employee Self Service holds write on Employee. If it does, a non-empty `MANAGER_EDITABLE` would be a REST door. This is one more reason for SEC-4.
- The ignore_permissions count in our app code (excluding tests) is 366 lines (grep, this worktree). I did not find a counter gate under `scripts/` by file name. The new code must add none on Employee writes beyond the Version insert that `my_profile` already uses.

## 10 · Residual risk

| Risk | Kind | Owner | Accepted? |
|---|---|---|---|
| A manager reading a team member's home address leaves no log | intentional trade-off (logging views would be a new mechanism for one card) | Surbhi | **not yet accepted**: needs her name and date |
| An HR person who reports can still save Left alone in Desk | acceptable simplification (true today without this slice) | Surbhi | not yet accepted |
| Refusals not observable where ALV-391 is not deployed | temporary debt (removed when ALV-391 reaches main) | Surbhi | not yet accepted |
| Retention of the notice undecided | **blocks main** | counsel via Surbhi | – |

## Subtract pass

Removed: a per-view audit log for the personal details card (a new mechanism; listed as residual risk instead); a scheduled check for roles that lose their last holder (SEC-7's send-time refusal covers it); a separate requirement for leavers' details (folded into SEC-2); a separate cache requirement (folded into the SEC-1 test and OPS-6); a reason-for-leaving control (nothing is collected). The timeline line is held back by default (Q1).

## Sources

- [Amss Shardul: Enforcement of the DPDP Act and notification of the DPDP Rules](https://www.amsshardul.com/insight/enforcement-of-the-dpdp-act-and-notification-of-the-dpdp-rules/) (read 22 Nov 2026)
- [Hogan Lovells: DPDP Act brought into force](https://www.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-) (search result only, for the 13 May 2027 date)
