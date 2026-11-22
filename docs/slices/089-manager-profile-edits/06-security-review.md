---
slice: 089-manager-profile-edits (ALV-431, ALV-433)
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-22
risk tier: 1
verdict: NO BLOCKER (re-review after round 2, 3f792c29). F1 and F2 closed. One new Major (P2, F3 erasure of the outcome bell). NOT READY FOR MAIN (PRIV-4, P1, counsel).
---

# 089 · Security and privacy review

**What I read.** Worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`. I started at `bc8450be`. During the review HEAD moved to `8d93ef37` (DevOps doc only, `07-devops-inputs.md`). The code I reviewed is the same at both. Diff `git diff origin/dev...HEAD`, with `origin/dev` at `c472f179`. The branch is not rebased on that `origin/dev`. Frappe source was read only, inside `alv089-bench` (Frappe `16.33.1`, commit `988e54f`). **I ran no tests and opened no site.** That container was in use by another session, and two runs on one site break each other. Test results below are quoted from `03` and `04`, and labelled as such. No server was touched.

**Labels.** **Code** = I read the line named. **Their run** = the engineer or test engineer ran it (from `03`/`04`); I did not re-run it. **Inferred** = my reasoning. **Not checked** = I did not look.

**⚠ Builder and reviewer are the same (lesson 6).** I wrote `01c`. Here I am checking my own requirements. Finding F2 below is a gap in my own SEC-7. **A second reader should check SEC-7, SEC-9 and SEC-10** (`hrms-technofunctional-reviewer` is the natural one).

## Bad news first

1. **F1 (Major, P2): the reporter can share their own leaver ToDo with anyone, including "everyone".** Frappe's ToDo gives role `All` the `share` and `write` rights, and the ToDo controller lets the owner in. The reporter is the owner of every ToDo the report makes. No 089 hook guards `DocShare`. So a manager can make "Confirm that Ravi left. Last working day 30 Nov" readable by every login on the tenant. With a write share, a second login can rewrite the text HR reads, or close the ToDo, which declines the report. SEC-9 and SEC-10 are only partly met.
2. **F2 (Major, P2): the confirmers are picked by company, not by branch.** A branch-scoped HR person (for example one store's HR) who holds the confirming role gets the ToDo for a person in another branch they cannot open. That is lesson 2 again (slice 030), and the gap is in my own SEC-7.
3. **PRIV-4 (retention of the notice) is still not met.** Counsel has not answered. Per `01c` this blocks main, not dev.
4. **SEC-5 can be observed only if `test_security_log_alv391` is green.** `04` D-6 left it failing in one CI-shaped run (quarter 4). It is not settled.

## 1 · Threat model check (did the build change it?)

`01c` §1 still holds. Two things changed. The timeline Comment is not written (Surbhi, P-12), so the skip-level reader worry in Q1 is gone. And the "change emergency contact" half is deferred, so there is **no manager write to Employee in this slice at all**. One new door appeared that `01c` did not list: Frappe's sharing on the ToDo (F1).

## 2 · Requirement status

| Req | Status | Mechanism (file:line) | Proof |
|---|---|---|---|
| **SEC-1** ALV-433 cut | **met** | `hr_api.py` scorecard field list now `name, employee_name, designation, department, branch, date_of_joining, status, image` (diff hunk at ~1183). The detail reader has the same list (~1532). Both add `personal` from one helper, `leaver_report.personal_details` (`leaver_report.py:76-87`). | Code. I grepped `hr_api.py` for `personal_email`, `company_email`, `"cell_number"`, `"gender"`. The only hits are `_get_employee` (309-310), which is the caller's own record. Their run: `test_nothing_personal_is_sent_by_default`, QA `test_personal_email_gender_company_email_never_appear_even_when_everything_is_ticked`. Tick, untick, no restart: AC-36 to AC-38. |
| **SEC-2** who gets personal details | **met** | `is_direct_active_report` (`leaver_report.py:67-73`): `reports_to == caller's Employee`, the person is Active, and it is not the caller. The caller's Employee comes from `_get_employee`, which filters `status: Active` (`hr_api.py:304-311`, lesson 3 holds). It is **not** `get_effective_manager`, so the HR fallback (`alvoraa_goals/permissions.py:64-71`) opens nothing. Ticks are read live and intersected (`leaver_report.py:84`). | Code. Their run: QA `TestWhoIsRefusedPersonalDetails` (other team's manager, Left manager, Left person, closed list), with allowed cases beside it. Break-tested in `04` §3 (Active check removed → phone appeared). |
| **SEC-3** settings are access-granting | **met** | Both keys are in `ACCESS_GRANTING` (`settings.py` ~301-302). `set_cover_setting` sends them to `_set_access_setting`, which refuses anyone without System Manager and logs it. `off_list` refuses off-list names (~488-500). A Version row is written in the same transaction (~628-636). `set_people_setting` forwards there and does not decide anything itself. | Code. Their run: AC-32, AC-33; QA `test_the_candidate_list_is_exactly_the_closed_list...` (break-tested). |
| **SEC-4** ALV-266 exception | **not applicable: deferred, and the pin holds** | `employee_field_rights.py` is not in the diff. `MANAGER_EDITABLE = ()` (line 94). In non-test code the diff has no write to Employee: the only writes are ToDo insert, Notification Log insert, two `db.set_value` on ToDo and one `db.delete` on ToDo. | Code (diff grep). Pin `test_leaver_report_089.py:658`. **So the "ALV-266 exception limited to this path" question has a simple answer: there is no exception in this build.** |
| **SEC-5** refusals logged | **met in code; observability not settled** | Every refusal goes through `access.refuse` (`access.py:96-98`). The log line carries user, endpoint, doctype, name and rule only (`access.py:70-93`). The two old bare throws now log (`hr_api.py` ~1172, ~1526). `frappe.log_error` calls pass a message, so no traceback with local values is stored. | Code. Their run: the line is read from the handler. **But `04` D-6: `test_security_log_alv391` failed in a full quarter-4 run.** Not checked: whether the ALV-391 logger fix is on main and production. |
| **SEC-6** report endpoint | **met** | `send_leaver_report` (`leaver_report.py:98-175`): POST only, `_limited(... limit=10)`, no `allow_guest`. One refusal sentence for "no such person / not yours / yourself" (118), Active check (121), date window (125-138), row lock and one open report (142-150). It writes only ToDos. It never writes `status` or `relieving_date`. | Code. Their run: `test_refusals_write_nothing_and_are_logged`, `test_the_date_window`; QA `test_no_leaving_date_reaches_positions...` (break-tested). |
| **SEC-7** recipients, no share | **partial (F2)** | `_recipients` (`leaver_report.py:178-190`): holders of the role who also hold a role that can save Left, minus the reporter and the person, and `row.company in permitted_companies(u)`. `permitted_companies` fails closed (`access.py:238-260`). No `assign_to`, so no automatic DocShare (`leaver_report.py:8-15`). **No branch check.** | Code. Their run: `TestTwoCompanies`; DocShare count unchanged at send. |
| **SEC-8** confirming role | **met** | `eligible_confirmers` (`settings.py` ~661-680) returns nobody for `BROAD_ROLES` or an unknown role. It is checked at save (~531-547) and again at send (`_recipients`). Cap of 10. | Their run: AC-32, QA cap test with 11 real holders. Minor wording issue: a broad role is refused with "Nobody holds Employee", which is untrue but safe (P4). |
| **SEC-9** reporter cannot change or remove | **partial (F1)** | `guard_todo` (`leaver_report.py:224-248`) on ToDo `validate` and `on_trash` (`hooks.py` ~590-594). It refuses any change by the reporter, any change to the marker or date by anyone, and a hand-made marked ToDo. `assign_to.remove` and `update_comment` cannot reach these rows: no reference and no Comment. **The `frappe.share.add` door is open.** | Their run: `TestGuard` (set_value ×3, save, delete; forged insert). Break-tested in `03`. |
| **SEC-10** who reads the notice | **partial (F1); tenant read owed** | ToDo: `allocated_to`, `assigned_by` or `owner`, or a role with a non-automatic ToDo row, which is System Manager as standard (Frappe `todo.py:149-173`, read). Bell: `for_user` only. No Comment, so nothing on the Employee timeline. | Their run: QA `test_nobody_outside_the_circle_reads_the_notice` (colleague, other manager, skip-level, other-company HR, guest; break-tested with Custom DocPerm). **Not checked: Custom DocPerm rows on ToDo, or `disable_document_sharing`, on any tenant.** |
| **SEC-11** what the notice says | **met** | Built on the server from record values. `escape_html` on the ID, the name and the reporter's name (`leaver_report.py:156-158`; bell text 273-276, 295-296). No personal field, no free text. JS escapes every value it draws (`portal.js` diff, `esc(...)` throughout the personal card and notes). | Their run: AC-26 `<b>x</b>`. Code for JS. |
| **SEC-11b** never emails | **met** | Plain ToDo insert. Frappe's ToDo controller sends no mail (`todo.py:40-76`, read). The bell is type `Alert`, which is in `notification_skip_email_types` (Frappe `hooks.py:82`), and `is_email_notifications_enabled_for_type` returns False for it (`notification_settings.py:83-85`). | Code (Frappe source). Their run: Email Queue count unchanged. **Not checked: a tenant's own `Notification` rule on ToDo would still send mail** (release read, OPS). |
| **SEC-12** CSRF really runs | **met** | `methods=["POST"]` on the new endpoint. The settings setter is existing code. | Their run: `TestARealRequest` over real HTTP: no token 400, GET 403, 11th POST refused; plus a `/tmp` run outside the test runner. Break-tested. |
| **PRIV-1** closed lists | **met** | `MANAGER_SEES_FIELDS` is exactly five fields (`people_fields.py` ~86-92). All five are level 0 (`SELF_EDITABLE`, `employee_field_rights.py:74-78`). **None is in `LEVEL_1` (66-70) or `LEVEL_3` (85-88)**, so no level 1 or level 3 field can be offered or saved. An exact-set pin stops any addition. Default `""` (`settings.py` ~112). | Code. Their run: `test_fresh_defaults`, QA exact-set pin (break-tested by adding `personal_email`). |
| **PRIV-2** the person is told | **met in code; notice wording open (Q3)** | `open_report_about` (`leaver_report.py:211-219`) is called only with the caller's own record (`my_profile.py` ~130). It returns the reporter's name and the date, and never the confirmers. | Their run: AC-22 to AC-24. The card caption "Staff can see that you can" is still not a privacy notice: counsel Q3 open. |
| **PRIV-3** not a leaving fact | **met** | Nothing writes `relieving_date` or `status`. The Team line uses `open_reports_by(... assigned_by=caller)` only (`leaver_report.py:195-208`). | Their run: QA Positions and Team assertions (break-tested). |
| **PRIV-4** retention | **NOT MET: counsel pending (blocks main)** | Fail-closed default in place: one copy only (the ToDo rows and a bell), no DocType, no export, no log line with the date. The Employee `on_trash` deletes the ToDos (`leaver_report.py:301-308`). Read today: Frappe clears Notification Log after 180 days (`notification_log.py` `clear_old_logs(days=180)`), but the ToDos have **no end date**. That sits against counsel's 18 Sep line "no soft-delete for ever" (memory note, Surbhi's report of counsel, not counsel's written words). Not checked: whether a confirmer's delete of a ToDo leaves a Deleted Document copy. | No test, by design until counsel answers. |

## 3 · Findings

### F1 · Major, P2 · The reporter can share the notice (SEC-9, SEC-10)

**Who, how, what.** Meena is a plain manager. She sends a report about Ravi. She calls `frappe.share.add("ToDo", <her ToDo name>, everyone=1)`. She can list the ToDo names because she owns them. After that, every login on the tenant can open "Confirm that Ravi left. Last working day …. Reported by Meena". With `write=1` to a second login, that login can rewrite the description HR reads, or close the ToDo. Closing it declines the report and closes all the sibling ToDos (`on_todo_update`, `leaver_report.py:260-278`).

**Why it works (Code, Frappe 16.33.1).**
- `todo.json`: role `All` has `share` and `write`. Every login holds `All` (`permissions.py` `get_roles`, `roles += [ALL_USER_ROLE, GUEST_ROLE]`).
- `todo.has_permission` returns True for the `owner` (`todo.py:164-173`). Frappe sets `owner` to the reporter, because the inserts run in her session (`leaver_report.py:163-168`).
- `share.check_share_permission` needs only those rights (`share.py:231-265`). It is whitelisted (`share.py:21`).
- A share then overrides the ToDo controller's refusal for the reader (`permissions.py` ~209-211, `false_if_not_shared` after `get_doc_permissions`).
- The only `DocShare` validate hook is the grooming one (`grooming.py:611-625`), which looks only at grooming records.
- `guard_todo` refuses the **reporter's** edits only. A sharee's edit to the description or status passes (`leaver_report.py:244-248`).
- Frappe's own block is `disable_document_sharing` (`permissions.py:112`). **Not checked on any tenant.**

**Not run.** I could not use the bench. The evidence is a read of code, which is the bar for a Major. Inferred and not read: list views also show shared rows.

**Fix (smallest, existing pattern).** One `validate` check on `DocShare`: refuse when `share_doctype == "ToDo"` and the ToDo carries `alv_leaver_employee`. Put it beside the grooming hook in `hooks.py` ~596. Test it as the reporter over `frappe.share.add`, with `everyone=1` and with `write=1`. Break-test it.

### F2 · Major, P2 · Confirmers are scoped by company, not branch (SEC-7, my gap)

**Who, how, what.** A tenant gives branch-scoped HR people (a Branch User Permission for Employee) the confirming role, for example `HR User`. A manager reports someone in another branch of the same company. That HR person's ToDo list then shows the person's name, the last working day and the reporter. Yet they cannot open the Employee or save Left. It is a notice to someone with no right to act on it.

**Why (Code).** `_recipients` checks `row.company in permitted_companies(u)` only (`leaver_report.py:188-190`). `permitted_branches` exists and is not used (`access.py:263-280`). **Not checked:** whether any tenant has branch-scoped holders of a role that could be chosen. The default role is `HR Manager`. Memory notes say DTC uses narrow per-doctype User Permission rows, which makes this likely, not proven.

**Fix (framework first).** Replace the company test with `frappe.has_permission("Employee", "write", doc=row.name, user=u)`. That one check covers company, branch and every User Permission, and it also proves SEC-7(b) "can actually save Left" for that person. Test it with one branch-scoped holder.

### Minor and notes

- **P3:** a confirmer can change `allocated_to` or the description. HR is trusted, and ToDo `track_changes = 1` writes a Version row on that save (read in `todo.json`). Note only.
- **P4:** the reporter, as owner, can list the ToDos and so sees the confirmers' user IDs. PRIV-2 forbids this only for the **person reported**, and that holds. Note only.
- **P4:** the auto-close is a `frappe.db.set_value` (`leaver_report.py:272`, `293`). It writes no Version row on the ToDo. The Employee save that triggers it does write one, so the audit trail exists on the Employee.
- **P4:** the SEC-8 refusal for a broad role says "Nobody holds Employee". It is wrong but safe.
- **Unneeded surface:** none found. There is one Custom Field, no new DocType, route, export, cache, queue or scheduler job, and one `ignore_permissions` (the bell, pinned at `test_portal_security_010.py` ceiling `leaver_report.py: 1`).
- **Lesson 2 sibling grep.** Outside the caller's own record (`hr_api.py:309`), the other readers of `cell_number`/`personal_email` in `alvoraa_portal/*.py` are `performance_api.py:2077-2130` (server-side email addressing, never returned) and comments in `staff_api.py` and `frame_api.py`. The joiner files hold the person's own data. None sends these fields to a manager.

## 4 · Cross-tenant and cross-company

- **Cross-tenant: no path found (Inferred from Code).** Every read is the site's own database. Settings are site `DefaultValue`. `_FLAG` lives in request-local `frappe.flags` and is reset in `finally` (`leaver_report.py:161-174`). The rate limiter uses the site-namespaced cache. There is no module-level cache in `leaver_report.py`.
- **Cross-company: closed for the confirmer list** (`permitted_companies`, fails closed). **Their run** proves it with two companies. Branch: F2.

## 5 · Compliance verification table

| Obligation | Source and date | Status in this slice |
|---|---|---|
| DPDP Act 2023: reasonable security safeguards | `01c` §4: secondary source read 22 Nov 2026. The baseline file says 24 Aug 2026, **90 days today; stale from tomorrow.** I did not re-verify it today. | Access control and refusal logging met, except F1 and F2 |
| DPDP Rules 2025: logs kept "for at least one year from the date of such processing" | `01c` §4: a secondary note, read 22 Nov 2026. The Gazette text was not read. | Feeds PRIV-4. Bells are cleared at 180 days. Counsel must say whether the rule applies to a leaver notice |
| Purpose limitation, minimisation | baseline §2, 24 Aug 2026 | Met: closed five-field list, default empty, three fields cut |
| Notice | baseline §2, 24 Aug 2026; memory note of 31 Oct 2026 ("the notice is the employer's") | Open: Q3 |
| Counsel 18 Sep 2026 (no soft-delete for ever), counsel 21 Nov 2026 (attendance and pay kept 5 years) | memory notes; Surbhi's report, **not counsel's written words** | Neither covers a leaver notice. PRIV-4 open |

I am not a lawyer. The retention and notice rows need counsel.

## 6 · What must exist for each control to be observable (lesson 1)

- **F1 fix:** a ToDo made by the manager's own session (owner = manager). A report made by Administrator in a test would make the share door look closed.
- **F2 fix:** a holder with a Branch User Permission. On a site with none, "no extra recipient" proves nothing.
- **SEC-5:** the ALV-391 fix deployed, and `test_security_log_alv391` green in a full CI quarter 4.
- **SEC-10 and SEC-11b on a tenant:** a read-only query per tenant before main of Custom DocPerm on ToDo, `Notification` rules on ToDo and `disable_document_sharing`.

## 7 · Residual risk (each needs a name and a date; none is accepted yet)

| Risk | Kind | Owner | Accepted? |
|---|---|---|---|
| F1: the reporter can share the notice | **temporary debt** (a one-hook fix removes it) | Surbhi: fix, or accept in writing before main | **not yet** |
| F2: branch-scoped confirmers | **temporary debt** (one-line fix) | Surbhi | **not yet** |
| PRIV-4: ToDos kept with no end date; counsel not answered | **dangerous debt: escalate now** (P1 for main) | counsel via Surbhi | – |
| A manager reading a team member's address leaves no log (`01c` §10) | intentional trade-off | Surbhi | **not yet** |
| An HR person who reports can still save Left alone in Desk (`01c` §10) | acceptable simplification | Surbhi | **not yet** |
| Refusals not observable where ALV-391 is not deployed; D-6 unsettled | temporary debt | Surbhi | **not yet** |
| System Managers read every ToDo, leaver notices included (Frappe standard row) | acceptable simplification | Surbhi | **not yet** |

## 8 · Verdict

**No Blocker.** The core controls hold in code. Only a direct manager of an Active person, signed in as an Active employee, can read the ticked fields or send a report. The four ALV-433 fields are gone from both readers. The allow-list is closed at the setter and again at every reader. No level 1 or level 3 field is on it. There is no manager write to Employee. The report never emails, never assigns and never shares on its own, and settings changes write a Version row.

- **For dev:** acceptable once Surbhi has the two P2 findings in front of her. My recommendation is to fix F1 and F2 first. Each is one small change with one test.
- **For main: not ready.** That needs PRIV-4 from counsel (P1); F1 and F2 fixed or accepted in writing; `test_security_log_alv391` green in CI; the per-tenant reads in §6; and a rebase on current `origin/dev`.

**Not verified by me:** any test run (all results are from `03` and `04`), any tenant's settings, and whether dev or production run the same Frappe as `alv089-bench`. To close these I would need my own stack, or the slice stack while nobody else is using it, plus a read-only query on each tenant.

## Subtract pass

Removed: a finding on the confirmer editing the description (HR is trusted, and a Version row exists, so it is a note); a separate finding on the confirmer IDs the reporter can see (PRIV-2 does not cover the reporter); a re-statement of the AC table (it is in `04`). Kept: F1 and F2. Each names an actor, a door and the data.

---

# Re-review after round 2 (22 Nov 2026)

**What I read.** Same worktree and branch, HEAD `3f792c29`. Diff `git diff 0cfdb0c3..HEAD` (fixes `83198828`, `3f792c29`). Branch is local only: `git branch -r --contains 0cfdb0c3` is empty, so no leaver ToDo, share or bell exists on any tenant. Frappe source read inside `alv089-bench` (16.33.1). **I ran no tests.** Another session was running `test_leaver_report_089` on `test_site` while I worked, and two runs on one site break each other. Test results are **their run** (`03` round 2 table, with break tests), not mine.

**Same person again (lesson 6).** I wrote `01c` and the first review. The second reader for SEC-7, SEC-9 and SEC-10 is still owed; this section does not replace it.

## Bad news first

1. **F3 (Major, P2, new): deleting an Employee no longer deletes the outcome bell.** The fix moved the bell to `document_type "ToDo"` with `document_name` = the Employee ID (`leaver_report.py:271`). Frappe deletes bells by that pair (`model/delete_doc.py:509`), and `on_employee_trash` (`leaver_report.py:316`) deletes ToDos only. So: HR deletes Ravi's Employee to honour an erasure request; Meena's row "Confirmed: Ravi left on ..." stays in her bell until Log Settings clears it (method default 180 days, `notification_log.py:71`; per-tenant setting **not checked**). The reader is the reporter, who already knew, so this is not a Blocker. It is an erasure regression and it feeds PRIV-4. **Fix:** one more delete in `on_employee_trash`: Notification Log where `document_type = "ToDo"` and `document_name = doc.name`. Test: delete the Employee, count the bells. Also P4: Desk's bell links that row to `/app/todo/<employee id>`, which opens "not found".
2. **PRIV-4 is still not met** (counsel). Unchanged; F3 adds to it.

## Round-1 findings

| Finding | Now | Evidence |
|---|---|---|
| **F1** share door | **closed** | `guard_share` on DocShare `validate` (`leaver_report.py:254`, `hooks.py:596-598`). Code: every Frappe write path I found runs `validate`. `share.add` always does `doc.save(ignore_permissions=True)` (`share.py` ~79), and `flags={"ignore_share_permission": 1}` only skips `check_share_permission`, not `validate`. `set_permission` saves too. Desk's Share dialog calls `share.add`. Desk's Assign on a leaver ToDo (`assign_to._add`) shares with any assignee who cannot read it, so the guard refuses and the request rolls back; an assignee who can already read it (System Manager) needs no share. `frappe.client.insert` / `set_value` on DocShare save, so `validate` runs. No `db_insert` or SQL on DocShare in `alvoraa_portal` or `hrms` (grep, tests excluded). Shares made before the guard: none can exist (branch never left this machine; the ToDo names are new on each send). Their run: `test_the_reporter_cannot_share_the_notice` (one login with write, and everyone), break-tested. Not covered by the guard, and fine: raw SQL by a System Manager in a console. |
| **F2** branch scope | **closed** | `_recipients` adds `frappe.has_permission("Employee", "write", doc=row.name, user=u)` (`leaver_report.py:193`). Code (Frappe `permissions.py` 81-275, 353+): it uses `u`'s own roles, `u`'s User Permissions (Company, Branch, any link, applied when the row covers Employee), and the controller hook with `user=u`. That hook (`employee_field_rights.py:307-327`) returns True only for Administrator, `HR User` / `HR Manager` / `System Manager`, or the person's own record; anyone else gets False on an unchanged record. So: **Branch UP** - scoped (their run, break-tested). **Company UP** - scoped twice (this check and `permitted_companies`). **System Manager** - included only if their role row on Employee gives write and their UPs cover the person [not checked: the role row on any tenant]. **HR user with no UPs** - passes this check; `permitted_companies` (`hrms/alvoraa_hr_core/access.py`) then limits them to their own Active Employee's company, or nothing. A UP row limited to another doctype (DTC's narrow pattern) does not scope Employee, so that person gets the notice and can also open the Employee: the notice follows who can act, which is what SEC-7 asks. `print_logs` only writes to a flag list; the reporter sees no message about who was skipped. |
| **M-1** bell text | **safe from injection** | Write: `escape_html` on the employee name and the reporter name; the dates come from `_day(...)` on server dates, never from the caller (`leaver_report.py:156-158`, 288-292, 310-311). Read: `notices_feed` unescapes (`notices.py:146`) and all portal renderers escape again with `esc()` (`portal.js` 7988 `ntRowHtml`, used by the card and the page; 8034 detail; `esc` at 265 covers `& < > "`). Desk's bell shows the stored text, which is escaped. Who reads the rows: Notification Log query condition is `for_user = user` except Administrator (`notification_log.py:104-117`); System Manager gets no wider read. Their run: the reporter sees the line, four others do not. |
| **M-2** double send | **closed** | `get_values(..., for_update=True)` after the Employee row lock (`leaver_report.py:142-146`). A locking read sees committed rows, so the second request finds the first one's ToDos. Their run: `test_an_overlapping_second_report_is_refused`, break-tested. Inferred: the test shows the snapshot problem with the first request committed before the second sends, not two requests both waiting on the lock; the same current-read mechanism covers both. |

## New minor findings

- **F4 (Minor, P3): the portal bell now shows every ToDo-typed notice ungated, not just the outcome line.** `OWN_COPY` (`notices.py:46-47`) matches any Notification Log with `document_type "ToDo"`. Frappe writes these for share notices, assignments on a ToDo, mentions and tenant Notification rules, and the ToDo title is its description (`todo.json:200`). Scenario: any login makes a ToDo saying "Confirmed: Ravi left on 30 Nov", shares it with Meena with `notify=1`; her portal bell shows "X shared a document ToDo Confirmed: Ravi left ..." as text (escaped, so no script, and the sender is named). Before round 2, ToDo rows never reached the portal bell. **Fix:** count a ToDo row as own copy only when `type == "Alert"`. Not checked: whether any tenant has a Notification rule on ToDo.
- **F5 (Minor, P3, availability, Inferred): the locking read runs on a column with no index** (`alv_leaver_employee`, "no index: OPS-21", `leaver_report.py:17`). InnoDB locks every row it scans, so until the send commits, every ToDo write on the tenant waits, and a confirmer closing a leaver ToDo at the same moment can deadlock (one request fails and rolls back). Not measured. The ToDo index already waiting for Surbhi removes it; I now recommend it.

## Requirement status (changed rows only; all others as in section 2)

| Req | Was | Now |
|---|---|---|
| SEC-7 | partial (F2) | **met** (`leaver_report.py:191-193`) |
| SEC-9 | partial (F1) | **met** (`guard_todo` + `guard_share`) |
| SEC-10 | partial (F1); tenant read owed | **met in code; tenant read still owed** (Custom DocPerm on ToDo per tenant) |
| SEC-11 | met | **met**, re-checked for the bell (M-1 row) |
| SEC-5 | met in code; observability not settled | unchanged (`04` D-6 not re-run) |
| PRIV-4 | NOT MET | **NOT MET**, plus F3 |

## Residual risk (none accepted yet)

| Risk | Kind | Owner | Accepted? |
|---|---|---|---|
| F1, F2 | closed | - | - |
| F3: bell outlives the Employee's deletion | **temporary debt** (one delete in `on_employee_trash`) | Surbhi: fix before main | not yet |
| F4: ToDo-typed notices ungated in the portal bell | temporary debt (one filter) | Surbhi | not yet |
| F5: lock on an unindexed column | temporary debt (the index) | Surbhi, with DevOps | not yet |
| PRIV-4 | **dangerous debt: escalate now** (P1 for main) | counsel via Surbhi | - |
| Section 7 rows not named above | unchanged | Surbhi | not yet |

## Verdict

**No Blocker.** F1 and F2 are closed in code, with break-tested tests from the engineer. The bell text cannot carry HTML or script.

- **For dev:** acceptable once Surbhi has F3 in front of her. My recommendation: fix F3 and F4 first (one line each, one test each).
- **For main: not ready.** Needs PRIV-4 from counsel, F3 fixed, the second reader on SEC-7/9/10, `test_security_log_alv391` green in CI, the per-tenant reads in section 6, and a rebase on `origin/dev`.

**Subtract pass.** Removed: a note that `permitted_companies` is now redundant beside `has_permission` (it is a second fail-closed check and costs nothing; deleting it is not my call); a note on Frappe's `<b>` tags showing as text in share notices (cosmetic, inside F4). Kept F3, F4, F5: each names an actor, a path and what is seen or lost.
