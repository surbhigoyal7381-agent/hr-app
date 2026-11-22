---
slice: 089-manager-profile-edits (ALV-431, ALV-433)
artifact: 00-impact-analysis (impact analysis and strategy; no code written)
author: hrms-fullstack-engineer
date: 2026-11-22
risk tier: 1 (who can see what, personal data, a date that stops pay)
status: waiting for Surbhi's approval (CLAUDE.md §2 step 3)
---

# 089 · Impact analysis and strategy

## What I read, and what I did not

- **Worktree** `/Users/mac/hr-app/.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, HEAD `27eeb574`, built on `origin/dev c9d702f0`.
- **Frappe source:** read inside the running container `alv085-bench2` (image `ghcr.io/surbhigoyal7381-agent/hr-app:dev-3830ed3`). **Frappe v16.33.1** (commit `988e54f`), **ERPNext v16.34.2**. The same image runs `alv396-bench` (Frappe 16.33.1 confirmed there too). **Not checked:** that dev and production run this same Frappe. Both read-only; nothing run, nothing started, no data read.
- **Labels:** *proven* = I read the line named. *inferred* = my reasoning. *not checked* = I did not look.
- This build is **"see" only**. The "change" half (US-10, US-11, ACs 31 and 43 to 48, P-9, P-14, P-17) is deferred. There is **no Employee timeline comment** (P-12 not built, AC-27 stands).

## Bad news first

1. **The spec's Team-list target is wrong.** The spec (§0, G5, AC-49, AC-52) puts the "Reported, not yet confirmed" line on `team_api`. *Proven:* the Team cards the manager taps today are drawn by `portal.js` from **`hr_api.get_manager_dashboard`** (JS call at `portal.js` l.14468, card markup l.14518, which calls `openEmpScorecard`). `team_api.get_team` feeds only `next-team.js` (the `hrms-employee-next` shell), whose own header says the Scorecard link "is not built". Prototype v4 draws "the card opens the Scorecard as today", so the line goes in **`get_manager_dashboard` and `portal.js`**, and `team_api.py` / `next-team.js` are **not touched**. *Not checked:* whether any tenant uses the `next` shell. Needs Surbhi's one-word confirm (Q1).
2. **Frappe's own ToDo code would break two decisions if I set `reference_type` / `reference_name`.** *Proven, Frappe 16.33.1, `desk/doctype/todo/todo.py`:* on every save `ToDo.on_update` calls `add_assign_comment`, which writes a Comment ("assigned ...: <description>") **on the referenced Employee**; and `update_in_reference` writes the confirmers' user IDs into the Employee's `_assign` column. That is the Employee timeline line Surbhi said not to write (and the skip-level leak behind it), and it names the confirmers (PRIV-2 says never). So **the ToDo must not reference the Employee.** See "How the ToDo is made".
3. **A forged leaver ToDo is a new door the spec did not list.** *Proven (`todo.json`):* role `All` has create, write and delete on ToDo. Any manager could `frappe.client.insert` a ToDo carrying my marker field for any person, which would block that person's real report ("already reported") or mislead the Employee-save auto-close. SEC-9 only guards edits by the reporter. I add the insert door to the same guard (three lines).
4. **"Set Left" is refused by ERPNext when the leaver still has Active direct reports.** *Proven, `erpnext/setup/doctype/employee/employee.py` l.275-292* (`validate_status`, raises "Cannot Relieve Employee"). A manager who reports a person with their own team will see the ToDo stay open until HR re-points those reports. Nothing for this slice to fix; AC-19 already says we write nothing to `reports_to`. Said here so nobody is surprised at the dry run (OPS-16).
5. **A confirmed Left also switches off the person's login.** *Proven, `employee.py` l.172-178, 300-308:* `on_update` → `update_user_status` disables the User. So the reporter's *outcome* bell goes to a still-enabled manager, but the leaver's own My profile line disappears the same instant their login does (harmless, listed in side effects).
6. **ToDo rows are not removed when an Employee is deleted unless they reference it.** *Proven, `model/delete_doc.py` l.501-502* (`delete_dynamic_links` deletes ToDos by `reference_type`). Because I must not set the reference (point 2), a deleted Employee would leave an orphan ToDo naming the leaver. This is the PRIV-4 "not checked" item, now answered. My fix is one line in the Employee `on_trash` (Q4, needs her yes).
7. **The rate-limit sentence has no number.** `field_app_limits._limited` (the pattern OPS-12 names) answers "Too many tries. Please wait a while and try again." *Proven, l.82-88 and `field_app_errors.py`.* AC-55 asks for "the wait in plain words". The wait number only travels in the field-app JSON body, which the portal does not read. **My default: accept the existing sentence** (it says what to do next). Say no and I write a 6-line limiter of my own (Q5).

## Dev moved: yes, two commits, none in my files

`git fetch origin dev`: `origin/dev` is now **`4df25095`** (I built on `c9d702f0`). **Incoming, read:**

| Commit | What it changed |
|---|---|
| `4df25095` ALV-432 | `portal.js` (two spots, `acForm` ~l.7074 and `trAskForm` ~l.16553) and a DOM test `portal_correction_test.js` |
| `8407830c` sidebar pinned | `portal.js` (`initSbCollapse` ~l.25786), a DOM test `portal_sidebar_pinned_test.js`, `scripts/run_dom_tests.js` (4 lines) |

4 files, 184 insertions, none in `hr_api.py`, `hooks.py`, `team_api.py`, `settings.py` or the Team/Scorecard/Administrator parts of `portal.js` (my regions are ~l.8732, ~l.14080 and ~l.14468-14520). **I will rebase on `origin/dev` before I start and before each commit.** Those two commits are someone else's; I will not touch them.

## Rung of the ladder

**New code on existing doctypes. No new DocType, no new app, no queue job, no scheduler job, no nginx change.**

| Cheaper rung | Why rejected |
|---|---|
| Already there: Frappe HR **Employee Separation** | A full exit process in Desk for HR. The manager cannot use it, it has no "reported, not confirmed" state, and it would hold the date before HR confirms it. (Brief §3; **I did not open its source.**) |
| Already there: `assign_to.add` for the ToDo | Shares the Employee record, emails the text, writes the timeline comment, names the confirmers. See below. |
| Configuration only | No Frappe setting makes a manager's tap create a confirmer's task. |
| A Notification / Assignment Rule | Fires on a document event, not on a manager's request; no per-company recipient rule. |
| New DocType | A table, permissions and a retention clock for a few rows a month (OPS-2 agrees). |

The one schema change is **one Custom Field on ToDo** (see below). Everything else is a few functions in one new file plus small edits.

## How the ToDo is made (the question the spec marked UNVERIFIED)

**Read in Frappe 16.33.1 (`desk/form/assign_to.py`, `desk/doctype/todo/todo.py`, `notification_log.py`).** `assign_to._add` does five things; only the first is wanted:

| What `assign_to._add` does (proven, l.58-146) | Wanted? |
|---|---|
| inserts a ToDo | yes |
| `frappe.share.add` (DocShare) when the assignee cannot read the record (l.106-118) | **No (SEC-7)** |
| `notify_assignment` → `enqueue_create_notification` (a Notification Log, and email if the user's settings allow, with the description unescaped, l.269-308) | **No (OPS-19, SEC-11)** |
| sets `Employee._assign` and a "Assigned" Comment (via `ToDo.on_update`, because it passes `reference_type`) | **No (decision 2, PRIV-2)** |
| `_follow_document` | no |

**So I do not call `assign_to` at all.** One plain insert per confirmer:

```
frappe.get_doc({"doctype": "ToDo", "allocated_to": <confirmer>, "assigned_by": <reporter>,
                "description": <escaped text with a link to the Employee form>,
                "date": <last working day>, "status": "Open", "priority": "Medium",
                "alv_leaver_employee": <employee id>}).insert()
```

- **No DocShare:** DocShare is written only inside `assign_to._add` (proven above). A plain insert never reaches it. Test: DocShare count unchanged (AC-12).
- **No email, no Notification Log:** `notify_assignment` is called only from `assign_to`. The ToDo controller itself sends nothing (read in full, `todo.py`).
- **No Comment, no `_assign`:** `ToDo.add_assign_comment` and `update_in_reference` both return at once when `reference_type` / `reference_name` are empty (proven, `todo.py`). So I leave them empty and carry the person in my own field.
- **Hook order is proven too** (`model/document.py` l.1633-1647): the controller runs first, then `doc_events` hooks. That matters for the guard below.
- **No `ignore_permissions`** on the ToDo insert. Role `All` holds create (proven), and `todo.has_permission` accepts `assigned_by == user`. This keeps the CI ceiling unchanged and fails closed on a tenant that tightened ToDo.

**The one Custom Field** on ToDo: `alv_leaver_employee` (Data, hidden, read-only, `search_index=1`). It is the marker *and* the person. **The last working day goes in ToDo's standard `date` ("Due Date", proven label)** instead of the spec's second field `alv_leaver_last_day`. That is one field instead of two, and the confirmer sees it as the due date. *Difference from spec G1a / AC-10 wording; harmless; Q2.* Created the way slice 080 does it (`create_custom_fields` in an `after_migrate` and `after_install` hook, `alternative_number.py`), so new tenants get it too.

**Who gets one (SEC-7), in bounded work:** (1) enabled users holding the set role: one `Has Role` read + one `User` read; (2) keep those holding a `LEVEL_2_WRITERS` role: one read; (3) **cap check here** (more than 10 → refuse, OPS-11), so the next step is at most 10 calls; (4) `access.permitted_companies(user)` includes the person's company; (5) drop the reporter and the person. Nobody left → "Nobody can confirm this yet. Ask HR.", nothing written (AC-65).

**Two taps at once (OPS-12):** the method first locks the Employee row (`frappe.db.get_value(..., for_update=True)`, a parameter I confirmed on `get_value` in this Frappe; `todo.py` uses it the same way), then checks for an open ToDo, then inserts. The second call waits, then gets "already reported". No duplicate rows.

## Approach, file by file

| File | Change | Mechanism |
|---|---|---|
| **NEW** `alvoraa_portal/alvoraa_portal/leaver_report.py` | the Custom Field + `after_migrate`; `report_leaver(employee, last_working_day)` (`@frappe.whitelist(methods=["POST"])`, `@_limited(SELF_KEY, "user", limit=10)`); recipients; `open_reports_for(employee_ids, reporter)` (one query); `my_open_report()`; ToDo guard hook; Employee `on_update` and `on_trash` hooks | New code, one file. All new queries live here so `hr_api.py` keeps its `ignore_permissions` ceiling of 67 (`test_portal_security_010`, proven) |
| `alvoraa_portal/hr_api.py` | `get_employee_scorecard` (l.1152) and `get_employee_detail_for_manager` (l.1491): cut the field list; add ticked fields from one shared helper; replace the two `"Access denied"` throws with `access.refuse`; add `open_report` and `can_report` to the scorecard. `get_manager_dashboard` (l.537): add one `reported` map | Extend |
| `alvoraa_portal/hooks.py` | `ToDo.validate` string → list (adds the guard after `grooming.refuse_side_record`); add `ToDo.on_update`, `ToDo.on_trash`; add one handler to `Employee.on_update` (before the photo hook, which says it must stay last) and `Employee.on_trash`; add `leaver_report.after_migrate` to `after_migrate` and `after_install` | Extend (hot file) |
| `hrms/hrms/alvoraa_org_structure/people_fields.py` | one candidate tuple (`cell_number`, `current_address`, emergency trio) and one `LIST_KEYS` entry | Extend. Closed list, same pattern as 078 |
| `hrms/hrms/alvoraa_org_structure/settings.py` | two keys into `ACCESS_GRANTING` (l.250) and `RULE_FOR_KEY`; one branch in `_set_access_setting` that refuses a bad role or a role over the cap | Extend. Gives System-Manager-only, refusal log and a Version row free (proven, l.447-460, 570-580) |
| `alvoraa_portal/people_settings.py` | the new "see" key in the allowed set and the payload; the role key | Extend |
| `alvoraa_portal/my_profile.py` | one `leaver_report` entry in `get_my_profile` (own record only) | Extend |
| `alvoraa_portal/public/js/ess/portal.js` + parts `appraisals.html` (Scorecard), `team.html` | the exit icon, the sheet, the reported note, the Personal details card, the Team grey line, the My profile line, the Administrator card and dialogs | Extend, as drawn in v4 |
| tests | see Test plan | |

Settings keys (new names; I grepped, none exist): `alvoraa_manager_sees_team_details` (list, default empty) and `alvoraa_leaver_confirm_role` (one role, default `HR Manager`). Not `alvoraa_manager_sees_whole_line_punches`, which already exists for something else.

**What each hook does:**

- **ToDo guard** (`validate`, `on_trash`): applies only to a ToDo with the marker. (a) New ToDo with the marker and not made by `report_leaver` (a server-side flag a browser cannot send) → refused (the forged-insert door). (b) Existing one, session user is `assigned_by` (the reporter) → refused on save and on delete. (c) Anyone changing the marker or the date → refused. Everyone else (the confirmer, System Manager) unaffected. `assign_to.remove` closes by construction: it finds a ToDo by `reference_type`, which mine does not have (proven, `set_status`).
- **Employee `on_update`:** first line returns unless `status` changed to `Left` (so an ordinary save of any employee costs nothing). Then one `UPDATE` closes the open leaver ToDos for that person (`frappe.db.set_value` on a filter, so it does not trip the reporter guard when HR who also reported saves Left), and one "Alert" Notification Log goes to each reporter ("Confirmed: ..."). **Wrapped so it can never fail an Employee save** (like the photo hook): any error → `frappe.log_error` with the employee ID only. It runs in the same transaction as the save, so a rolled-back save rolls it back too.
- **ToDo `on_update`:** when a leaver ToDo goes Closed/Cancelled and the Employee is *not* Left → one Alert to the reporter ("closed without being confirmed"). If the Employee is Left, stay silent (the Employee hook already spoke).
- **Notification Log type "Alert":** proven in `notification_skip_email_types = ["Alert"]` (`frappe/hooks.py` l.82) and `is_email_notifications_enabled_for_type`, so it **never emails**. Same pattern as `announcements.py` l.453 and `expense_evidence.py` l.1019. Subject HTML-escaped (Desk draws it as HTML).
- **Employee `on_trash`** (needs yes, Q4): delete the person's leaver ToDos and bell rows. Closes the orphan in bad-news point 6. Two lines.

## Every caller I will touch, counted

(`grep -rnE` over `*.py *.js *.html *.json *.md`, this worktree, excluding `docs/slices`; counts are matches I read.)

| Function or name | Callers found |
|---|---|
| `get_employee_scorecard` | **1** screen caller (`portal.js` l.14093 via `openEmpScorecard`); **5** test files (`test_leave_ledger_035`, `test_review_outside_010d`, `test_goal_cycle_035`, `test_review_copies_010d`, `test_numbers_match_035`). A grep of `tests/` for `personal_email`, `gender` and `company_email` listed 10 other files and **none of these 5** (proven by the file list; I did not read the 5 line by line). **I will grep each of the 5 again before editing.** |
| `get_employee_detail_for_manager` | **1** JS caller, `openEmpDrawer` (l.13276), which **has no caller of its own** (grep finds only its definition and a comment). It is the only reader of `emp.cell_number`, `emp.company_email`, `emp.personal_email` (`renderEmpDrawer` l.14406-14408). `renderScorecard` reads none of the four fields (proven by grep, 3 hits all in the drawer). **3** test files (`test_leave_ledger_035`, `test_review_outside_010d`, `test_numbers_match_035`) |
| `get_manager_dashboard` (`hr_api.py` l.537) | **1** JS caller (`portal.js` l.14468); tests in 5 files (`test_team_scope_034` ×6, `test_team_payload_045` ×2, `test_leave_privacy_045` ×4, `test_payslips_payload_043` ×1). `test_team_scope_034` reads this function's *source* and pins two strings and a `limit` spy on the first `Employee` `get_all` call. **My added query is a ToDo query, so neither trips; I still run that file.** (`hrms/pms/api.py` has a different function with the same name; untouched) |
| ToDo `validate` hooks | `refuse_side_record` is wired **5 times in `alvoraa_portal/hooks.py`** and **5 times in `hrms/hooks.py`** (Comment, ToDo, DocShare, Tag Link, File); the two ToDo lines are at `alvoraa_portal/hooks.py` ~l.579 and `hrms/hooks.py` l.340 (both read). Frappe merges `doc_events` across apps into a list (`frappe.get_doc_hooks`, `composer` l.1655). I change only the alvoraa_portal ToDo value from a string to a two-item list and **leave `hrms` alone**. A test proves all three run |
| Employee `on_update` hooks | `alvoraa_portal/hooks.py`: **6** handlers (read, l.311-334); `hrms/hooks.py`: **3** (l.259-263); plus ERPNext's own controller `on_update` (l.172-179). Mine is the 11th, placed before the photo handler |
| `people_fields.LIST_KEYS` | **6** matches (definition, `allowed`, `off_list`, `settings.py` l.469, and the 078 tests). Additive: a new entry, no signature change |
| `ACCESS_GRANTING` | read by **1** function (`set_cover_setting`, l.428); referenced in **3** test files (`test_register_194` l.288, `test_people_settings_078` l.44/236, `test_org_access_settings_012f1` l.78-79) |
| `set_cover_setting` | **1** caller in app code (`people_settings.set_people_setting` l.310) |
| `people_fields` importers | **8** modules (`register`, `api` ×2, `settings`, `joiner_public`, `my_profile`, `employee_photo`, `positions_profile`, `people_settings`). Additive only |
| `openEmpScorecard` | **2** call sites in `portal.js` (l.14306 inline `onclick`, l.14518 the card) plus its definition (l.14080) |
| `MANAGER_EDITABLE` | stays `()` (`employee_field_rights.py` l.94). I do not edit that file (AC-42) |

## Personas

| Persona | What changes |
|---|---|
| **Line manager** | New: exit icon on the Scorecard of an Active direct report, report sheet, grey line on the Team card, reported note. New: ticked personal details (phone, home address, emergency contact) on the Scorecard. Removed from the wire: personal email, company email, gender. Cannot act on a skip-level, HR-covered or Left person |
| **Confirmer (HR Manager by default)** | New Desk ToDo with a link to the Employee; the Employee save closes it. Nothing else changes in Desk |
| **Employee** | New quiet line on My profile while a report is open. Nothing to press |
| **HR Manager (not System Manager)** | Cannot change the two new settings (refused, logged). Stops receiving the four undrawn fields on the Scorecard call (Q3) |
| **System Manager** | New Administrator card (two rows now, not three) |
| **CXO** | No change. Nothing here is a total |

HRMS domains: **org structure** (reporting line read, Left status), **payroll** (a confirmed leaver stops pay; the nightly draft-slip job is run after the dry run), **attendance** (marking stops for Left; *not checked*), **appraisals/goals** (the Scorecard page only; same data). Not leaves, not learning.

## Verdict on the seven non-functional dimensions

| Dimension | Verdict | Why |
|---|---|---|
| Performance | **neutral** | Scorecard: +1 ToDo query. Team: +1 query for all reports at once (not per report, AC-52). My profile: +1 indexed query. Employee save: 0 queries unless `status` changed to Left. No cache added. *Not measured yet;* measured at build on a 50-report manager and a 3G profile (OPS-10) |
| Security | **improves** | Closes ALV-433 (four fields leave the wire). Adds a closed, System-Manager-only setting, a direct-report check that does **not** use `get_effective_manager`, refusal logging on two throws that logged nothing, and a guard on the ToDo's four doors plus the forged insert. New write door is POST-only, CSRF-checked, rate-limited |
| Reliability | **neutral** | One request, one transaction; no job to fail. Employee hook can never fail a save. Risk named: a hook on every Employee save (OPS-16 dry run proves it) |
| Scalability | **neutral** | At most 10 ToDo rows per report, one index. 50 reports → one query. No growth with headcount beyond the cap |
| Maintainability | **neutral** | One new file holds the feature; hot files get small edits. One new `doc_events` entry per event. Pin tests name the feature |
| Data integrity | **improves** | The Employee's `status` and `relieving_date` are never written by a manager. One open report per person, enforced under a row lock. ToDo and bell closed in the same transaction as the Employee save |
| Compliance / privacy | **improves, with a ⚠** | Minimisation (closed lists, both ends checked), notice to the employee, no leak to skip-level managers or other companies. ⚠ PRIV-4 retention of the notice is still counsel's (blocks main, not this build) |

**Nothing is marked "degrades."**

## SEC, PRIV and OPS: how each is met

| Item | How | Proof |
|---|---|---|
| SEC-1 ALV-433 | field list cut in both readers; ticked fields via one helper `_manager_visible_fields(person)` | JSON of both calls has none of the 8 keys; tick, call, untick, call, no restart |
| SEC-2 | `reports_to == caller's Active Employee` **and** person Active **and** ticked **and** on the closed list; `get_effective_manager` not used for fields | 8-caller matrix with an allowed case |
| SEC-3 | two keys in `ACCESS_GRANTING`; saved only by `set_cover_setting` | HR Manager refused + logged; System Manager writes one Version row |
| SEC-4 | **deferred** with "change"; `MANAGER_EDITABLE` untouched | pin test `== ()` (AC-42) |
| SEC-5 | `access.refuse` for every refusal, plus the two existing throws | read the line from the log handler (ALV-391 pattern) |
| SEC-6 | `report_leaver`: all refusals in 01b §4.2; writes only ToDos | one case per refusal, counts unchanged |
| SEC-7 | recipient steps above; plain insert; no `assign_to` | 2 companies; DocShare unchanged; reporter-as-HR gets none; empty role refused |
| SEC-8 | role branch in `_set_access_setting` | each named role refused; empty and no-HR-role holders refused |
| SEC-9 | guard hook (validate + on_trash) | as the reporter's own session, each door refused; confirmer closes fine |
| SEC-10 | read matrix; per-tenant `Custom DocPerm` count on ToDo before main | the 5-caller `get_list` / `getdoc` test |
| SEC-11 | description built server-side, name escaped | `<b>x</b>` name test |
| SEC-12 | `methods=["POST"]` on both new writes | real HTTP, with and without the token; break test: make it GET-able |
| PRIV-1 | closed tuple, empty default, setter refuses and reader re-intersects | fresh-site default test |
| PRIV-2 | `my_open_report` for own record only, no confirmer IDs | colleague gets empty |
| PRIV-3 | nothing writes `relieving_date`; Team line only for the reporter | `positions_profile` unchanged |
| PRIV-4 | **blocks main.** Orphan question answered (point 6) | counsel |
| OPS-11 | no queue or scheduler job; cap 10 at save and send | `hooks.py` diff holds none |
| OPS-12 | POST + `_limited` 10 an hour; one open report under a lock | 11th call refused |
| OPS-13 | no route, no nginx change | diff has no `deploy/nginx.conf` |
| OPS-14 | = SEC-1 | = SEC-1 |
| OPS-15 | no per-user text in any part; no cache on the Scorecard | render the parts for two users, strings match |
| OPS-16 | dry run of "set Left" on a copy, then the nightly slip job | recorded stdout and stderr; **I have read ERPNext's Left code (points 4 and 5); the dry run is still owed** |
| OPS-17 / 18 | no new data store; `frappe.log_error` with ID only on every `except` | release steps |
| OPS-19 | no email: plain ToDo insert, Alert-type bell only | `Email Queue` count unchanged with email on |
| OPS-20 | refusal at send time | empty-role test |

Data-doors checklist (`.claude/context/data-doors.md`): bypasses I add, **counted so the CI ceiling can list them:** `leaver_report.py` **2** `ignore_permissions` (the two Notification Log inserts for another user; I try to make it one helper), **1** `frappe.db.set_value` (the auto-close), and `frappe.get_all` reads in 3 places (team states, own line, duplicate check), all keyed on the caller. `hr_api.py` adds **0** `ignore_permissions`.

## Parallel-work check

| Item | State |
|---|---|
| Files I change that are hot | `alvoraa_portal/hooks.py`, `hr_api.py`, `portal.js` (shared files) |
| Recent others in them | `git log origin/dev --since="7 days ago"` on `hr_api.py`, `hooks.py`, `team_api.py` shows slices 087, 085, ALV-394 (all already in my base) |
| Incoming since my base | the two commits above, `portal.js` only, different regions |
| Work board `.claude/work-in-progress.md` | **stale** (last updated 12 Nov, 8 rows, no 089 row; no row names `get_employee_scorecard`, `get_manager_dashboard` or the ToDo hooks). I will add a 089 row when approved |
| Unmerged branches of other sessions that touch these files | **not checked** (140+ worktrees). **Surbhi: is anyone else working in `hooks.py`, `hr_api.py` or the 087/086 slice code?** |
| Plan | work only in this worktree; rebase on `origin/dev` before starting and before each commit; stage by path; the Employee/ToDo hook lines are two small list edits, so a clash would be at the line level and I will re-read them after any rebase |

## Test plan and where it runs

**Stack.** `hrlocal-bench` mounts the stale main checkout, and `alv085-bench2` mounts `085-fix-tmp` (another session's work), so **neither can run this branch** (`parallel-work.md` §4 and §9; memory "shared bench cannot test a branch"). I propose my own stack **`alv089-bench`, `alv089-db`, `alv089-redis`** on its own network, from the same image (`hr-app:dev-3830ed3`, Frappe 16.33.1) with `alvoraa_goals`, `alvoraa_portal` and `hrms` bind-mounted from this worktree, exactly as `alv396-bench` is wired (read from `docker inspect`: own network, three bind mounts, own sites volume). About 975 MB (measured figure in `parallel-work.md` §9); five stacks are running now, so I will check `docker stats` first. **Not checked:** how `alv396` seeded its test site. **I need your yes to create these containers and to run `bench migrate` on my own stack.** I touch no other container.

**Python tests** (new file `tests/test_leaver_report_089.py`, run one module at a time with `bench --site test_site run-tests --module ...` on my stack):

- Matrix, each with an allowed case: report (direct manager OK; skip-level, HR-covered, Left person, self, Left manager, other company, guest refused, counts unchanged); personal fields (8 callers); setter (HR Manager refused, System Manager one Version row, bad field, bad role, over cap).
- Two companies with one HR Manager each; the reporter's **own session** (not Administrator); real HTTP for CSRF (with and without the token).
- ToDo guard: the reporter calls `frappe.client.set_value`, `save`, `delete`, `insert` (forged marker) and `assign_to.remove`: all refused. Confirmer closes: works.
- Employee save to Left closes the ToDos and writes one Alert per reporter; a plain Active save writes nothing and runs no ToDo query (query-count assertion); Left refused by ERPNext when reports remain leaves the ToDo open.
- Hook wiring pin test: all three `ToDo.validate` handlers (`grooming`, `plans`, mine) still run. A pin test names slice 089 so a bad merge fails CI.
- `Email Queue`, `DocShare`, `Comment` and Employee `_assign` counts unchanged by a report (email switched on).
- 5 against 50 reports: same query count on `get_manager_dashboard`.
- Existing neighbours, one at a time: the 5 Scorecard test files, `test_team_scope_034`, `test_team_payload_045`, `test_portal_security_010`, `test_people_settings_078`, `test_org_access_settings_012f1`, `test_register_194`.
- **Break tests, committed first:** (1) remove the `reports_to` check, watch the skip-level case fail; (2) remove the guard's `assigned_by` rule, watch the reporter-delete test fail; (3) make `report_leaver` GET-able, watch the CSRF test fail; (4) call `assign_to.add` instead of the plain insert, watch the DocShare/Comment/`_assign` test fail. Each restored after.
- **DOM tests** (`alvoraa_portal/tests/*.js`, run by `scripts/run_dom_tests.js`, like `portal_correction_test.js`): icon present/absent per state, sheet focus and Escape, failure sentence, Personal details card shows only ticked rows, and the payload of the Send press is asserted (memory: "test what it sends").
- `python scripts/check_app_integrity.py` before every commit (memory).

**Release-time, not CI:** OPS-16 dry run on a copy; per-tenant ToDo `Custom DocPerm` count **and** a count of `Notification` and `Assignment Rule` rows whose document type is ToDo (a tenant rule there would act on my ToDos, `run_notifications` and the `*` `assignment_rule.apply` hook, proven in `hooks.py` l.172-178 and `document.py` l.1262); 360 px, 200% text and the 3G measure; native review of the Hindi strings; ALV-391 logger on the target branch (AC-60).

## Side effects I expect, said now

1. The four undrawn fields stop reaching **HR** on the Scorecard call too, not only managers (SEC-1 says "to anyone"). Nothing draws them, so no screen changes; any outside script reading them would break (grep found none in this repo).
2. A leaver with Active direct reports cannot be confirmed until HR re-points them (ERPNext refuses). The ToDo stays open. No reminder (dropped).
3. A confirmed Left disables the leaver's login and clears their My profile line at the same time.
4. Deleting a ToDo (a confirmer can) leaves the manager's row back to normal with no bell (the spec's residual risk).
5. Because the ToDo has no reference, it will **not** show in the Employee form's "Assigned to" sidebar or `_assign` column. The confirmer finds it in their ToDo list with a link to the Employee in the text. That is deliberate.
6. A migrate adds one Custom Field and one index on `tabToDo` on every tenant; the migrate queue must be checked first (memory: the permission clean-up filled it once). **This slice adds no `Custom DocPerm` change.**
7. My ToDos fire the `*` `on_update` chain once each (`assignment_rule.apply`, search index update, etc., all existing). Fine at ≤10 rows a report. *Not checked:* whether ToDo is in the sqlite search index.

## Decisions I need from Surbhi

| # | Question | My default | If different |
|---|---|---|---|
| Q1 | The live Team screen is the classic one (`get_manager_dashboard`), not `team_api`. Put the grey line there and leave `next-team.js` alone? | **Yes** | Also edit `team_api` and `next-team.js` (adds a second place and a hot-file edit) |
| Q2 | One Custom Field (`alv_leaver_employee`) and the date in ToDo's own Due Date, instead of two fields? | **Yes** | Two fields, as G1a |
| Q3 | On the Scorecard call, **HR** also stops receiving the four fields and gets **none** of the ticked ones (HR has Desk). AC-38 reads "HR by existing rights"; the smaller reading is none | **None for HR** | HR gets the ticked fields the same as a manager |
| Q4 | An Employee `on_trash` that deletes the person's leaver ToDos and bell rows (stops an orphan naming a leaver). Not a purge job | **Yes, two lines** | Leave orphans until counsel answers PRIV-4 |
| Q5 | Accept `_limited`'s "Please wait a while and try again" instead of a number of minutes (AC-55)? | **Accept** | A 6-line limiter of my own |
| Q6 | Create `alv089-*` containers and run `bench migrate` on them (my own stack only)? | **Yes** | I cannot run the Python tests |
| Q7 | Anyone else in `hooks.py`, `hr_api.py` or `portal.js` right now? | not checked | – |

Everything else follows the spec as decided on 22 Nov.

## Not checked

- Whether dev and production run Frappe 16.33.1 / ERPNext 16.34.2.
- Whether any tenant uses the `hrms-employee-next` shell.
- Whether ToDo is in Frappe's sqlite search index.
- Custom DocPerm, Notification and Assignment Rule rows on ToDo at any tenant (needs a site read, owed before main).
- How the `alv396` test site was seeded.
- The exact 360 px layout and 3G timing (nothing built).
- `get_effective_manager` for a person with no `reports_to` still returns the HR Manager employee (read, `alvoraa_goals/permissions.py` l.64-71); I did not run the Scorecard as that user.
- The Hindi strings.

## Subtract pass

Removed from my first plan: a second Custom Field (the date uses ToDo's own); an `assign_to` wrapper (not needed once the insert is plain); a custom rate limiter (reuse, Q5); a Team-list edit in `team_api.py` and `next-team.js` (wrong screen); a "change" endpoint and its limiter (deferred); any cache; any scheduled check for a role that loses its holders (the send-time refusal covers it). Kept, because removing it fails an SEC item: the ToDo guard hook, the Employee hook, the row lock and the cap check. Nothing else could go.

## Strategy gate: Surbhi, 22 Nov 2026

**APPROVED, with all recommendations.** This approves implementation on the local stack only. It does not approve any push or deploy.
- Q1-Q6: yes as recommended (classic Team screen; one Custom Field with the date in Due Date; HR gets none of the ticked fields; Employee on_trash; accept `_limited`'s wording; own `alv089-*` stack with migrate there).
- **No index** on `alv_leaver_employee` (DevOps OPS-21).
- Q7: slice 088 (branch slice/088-register-signature) added 22 lines to `alvoraa_portal/hooks.py` at about 23:20 IST on 22 Nov. Rebase onto origin/dev before each commit.
- OPS-22 stands: before main, a migration and set-Left dry run on a copy of real data.
