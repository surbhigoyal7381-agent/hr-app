---
slice: 089-manager-profile-edits (ALV-431, ALV-433)
artifact: 05-review (senior architect review, CLAUDE.md §2 step 5)
author: hrms-technofunctional-reviewer
date: 2026-11-22
risk tier: 1
---

# 089 · Review

**Verdict: SHIP WITH FIXES.** No P0 or P1. Two P2 defects need a fix (or Surbhi's written acceptance) before dev. First: the manager's outcome line ("Confirmed" / "closed without being confirmed") is written but never shows in the portal bell. Second: the double-send lock does not work under MariaDB's default isolation level. Both fixes are small. `SHIP` here means ready to present for a push decision. It is not permission to push.

**What I read and ran.** Worktree `/Users/mac/hr-app/.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits` at `bc8450be`, based on `origin/dev c472f179` (fetched today; nothing newer). I read every changed code file in full or around each hunk: `leaver_report.py` (all), the `hr_api.py`, `hooks.py`, `my_profile.py`, `people_settings.py`, `people_fields.py`, `settings.py`, CSS, template and `portal.js` hunks, and both new Python test files. I also read Frappe 16.33.1 `todo.py` / `todo.json` inside `alv089-bench` (read only).
**I ran:** `node scripts/run_dom_tests.js` → `27 run, 0 not run, 0 failed`. `python3 scripts/check_app_integrity.py` → exit 0, `1015 checks, OK`. A two-session isolation demo on a throwaway `mariadb:10.8` container (`rv089-scratch-db`, removed afterwards). Its output is in M-2.
**I did not run the Python suites.** The re-test is using `alv089-bench` / `test_site` right now, and a second run would clash with it. Every Python pass count in this review is the engineer's or the test engineer's figure. **I have not seen those counts myself.** The D-1 re-test result is also not seen.
**Incoming commits:** the rebase brought in three commits by `surbhigoyal7381-agent` (Surbhi's sessions): `039bab0a` and `c472f179` (ALV-435, the secret scan) and `b2d9e979` (ALV-434, +36 lines in `portal.js`, away from 089's regions). **04-test-report tested an earlier base (`968bfe0e`, before these commits).** I re-ran the DOM suite on HEAD and it passes. The Python suites have not been run on HEAD. The re-test should cover that.
**The impact analysis exists** (`00-impact-analysis.md`, approved 22 Nov). I checked it against the code. One claim no longer holds (m-3).

---

## Major (P2: fix, or Surbhi accepts in writing, before dev)

### M-1 · The outcome bell lines never reach the manager's portal bell (design decision D3 not delivered)

- **Where:** `leaver_report.py:251-257` (`_tell` writes `document_type: "Employee"`); `notices.py:42` `NOTICE_DOCTYPES = (grooming.MARK, grooming.REVIEW, ANNOUNCEMENT)`; `notices.py:84-90` (the bell's feed filters on exactly those types).
- **Scenario:** a manager reports Ravi. HR saves Ravi as Left. `on_employee_update` writes one Notification Log row for the manager, "Confirmed: Ravi Kumar left on 30 Nov 2026." The manager opens the portal, and `notices.notices_feed` reads only rows whose `document_type` is one of three grooming or announcement types. **The row is never listed or counted.** The same happens to the "closed without being confirmed" row.
- **Why it is wrong:** D3 (01b l.199, l.233) was chosen so that "a confirmed leaver [does not] quietly drop off the list and a closed report [does not] quietly return". That quiet drop is exactly what happens now. The brief's WOW ends with "the manager sees 'Payroll confirmed: last day 30 Nov'". Store managers do not use Desk (brief §3), so Frappe's own Desk bell does not help them. *Inferred:* I did not check the roles of each manager at a tenant.
- **Why the tests are green:** AC-17 and AC-18 only ask that a row is written. `test_left_closes_the_reports_and_tells_the_reporter` and the QA `test_the_outcome_bell_is_read_only_by_its_reporter` both read the row with `get_all` or `get_list`. **No test could have shown that the bell is empty.** 01b listed "Does the bell show this kind of notification?" as an engineer question (l.209). I found no answer to it in 00 or 03.
- **Smallest fix (decision for the engineer and Surbhi):** let `notices_feed` show the caller's own 089 rows. For example, admit `document_type == "Employee"` rows that carry a fixed subject marker, then add a test that calls `notices_feed` as the manager. *Inferred:* `grooming._readable` gates every non-announcement row and probably drops Employee rows, so this needs a small branch, not just one more name in the tuple. `notices.py` also has a statement ceiling (≤ 14, OPS-13). The other option is to accept "Option B: nothing" in writing and delete the two `_tell` calls along with the one `ignore_permissions` they need.

### M-2 · The "two taps at once" lock does not stop a second report (AC-5, server half)

- **Where:** `leaver_report.py:140-150`. The `for_update` lock on the Employee is followed by a **plain** `frappe.get_all("ToDo", …)`.
- **Scenario:** two requests for the same person overlap. For example, the manager uses two tabs or two phones, or retries while the first request is still on the server. Both requests have already done plain reads (`_get_employee()` at l.110, the Employee read at l.112). In InnoDB REPEATABLE READ, those plain reads fix each request's snapshot. Request B waits on the row lock until A commits. B's ToDo read then uses its **old snapshot**, sees no open report, and inserts a second full set of ToDos.
- **Proven:** `select @@global.tx_isolation` on `alv089-db` returns `REPEATABLE-READ`, and Frappe sets no other level (grep of `frappe/database/` finds no isolation setting). The two-session demo on a scratch MariaDB 10.8 printed: `B_got_lock E1` · `B_plain_count_after_lock 0` · `B_locking_count 1`. So after the lock, a plain read misses A's committed row, and a locking read sees it.
- **Why it is wrong:** AC-5 says "when both calls reach the server, then exactly one report exists". The code comment at l.140 and the notes' "Try again is safe" reasoning both rest on this lock. **The only test, `test_a_second_report_is_refused_and_writes_nothing`, sends one call after the other**, so it could never show a race (lesson 1).
- **Harm, honestly sized:** duplicate ToDos for the confirmers. The close paths shut every open row by the marker field, and the bell is de-duplicated per reporter. So nothing about pay or data is lost. The sheet disables Send while a request is running (`lvSend`, `s.sending`), which blocks the commonest double tap. That is why this is P2 and not P1. If Surbhi reads AC-5 strictly, it is P1.
- **Smallest fix:** add `for_update=True` to the `open_rows` `frappe.get_all` at l.143 (a locking read sees the latest committed rows). Add one test with two DB connections or two threads. Break it by removing the argument, and watch the test fail.

---

## Minor (P3: can ship, written down with an owner)

- **m-1 · Refusal sentences differ from prototype v4 and the ACs, and only one difference was disclosed.** `leaver_report.py:119`: "This person does not report to you…" (v4 and AC-6 say "{n} does not report to you…"). This one is disclosed in 03 §Differences #1, and the reason given is good: the name must not tell a caller who exists. `l.148`: "You already reported **this person** on…" (v4 `dup` and AC-9 name the person). **This one is not disclosed.** It has no such reason either: the caller has already passed the direct-report check, so naming the person tells them nothing new. The memory rule "prototype parity" needs Surbhi's yes for each difference. Owner: engineer, to restore the name in the duplicate sentence or get her yes.
- **m-2 · On a timeout, "Not sent" may be untrue.** `lvSend` shows "Not sent. We kept your date." on any error without a server answer, including the 15 s `CALL_LIMIT_MS` timeout, when the report may have landed. The admin save in the same slice already uses the portal's honest form, "No answer from the office. It may have gone through." This is disclosed as difference #6 but not approved. Owner: Surbhi (words), engineer.
- **m-3 · The impact analysis said "My profile: +1 indexed query" (00 l.146). After OPS-21 removed the index, it is an unindexed scan of `tabToDo`.** That scan now runs on every My profile load (`open_report_about`), every Team load and every Scorecard open. Frappe's `todo.json` has no `search_index` field (read). This is acceptable under OPS-21's "add when a count says so", but **no tenant ToDo count exists yet.** Owner: DevOps, at the per-tenant read (07 §5 item 3). Include the `tabToDo` row count.
- **m-4 · The confirmer cap counts holders across all companies, and the default role is never checked.** `_recipients` (l.185-187) returns nobody when more than 10 qualifying users hold the role, counted before any company filter. A group tenant with, say, 4 companies × 3 HR Managers is therefore refused for every report. The default `HR Manager` is not validated until someone saves the setting. In both cases the manager is told "Nobody can confirm this yet. Ask HR.", which hides the real reason. *Not checked* at any tenant. Owner: DevOps (holder count per tenant, already in 07 §5 item 3), then Surbhi if any tenant is over 10.
- **m-5 · No Hindi strings were added.** The brief §7 lists "Hindi words reviewed" under "needed before it ships". `translations/hi.csv` exists, and prototype v4 carries machine drafts. 03 calls this temporary debt. Owner: Surbhi decides whether DTC stores get it before or after release.
- **m-6 · The Python suites were not run on HEAD.** See the header. Owner: test engineer (the re-test running now).

<details><summary>Nits (P4, backlog)</summary>

- `guard_todo` l.246-248: a confirmer who changes the Due Date is told "cannot be changed by the person who sent it". The refusal is right, but the words describe someone else.
- `send_leaver_report` l.126: `getdate(None)` and `getdate("")` return today in Frappe, so a call with no date silently reports today. The "Give the last working day as a date" branch only catches junk strings. The screen always sends a date.
- `open_reports_by(…, user=None)`: no caller passes `user`. Delete the parameter.
- `panels.css`: `.lv-icon{flex-shrink:0}` sits on its own line by the topbar rules, apart from the main `.lv-icon` block. Merge the two.
- `test_the_endpoint_is_post_only_and_rate_limited`: the limit assertion only runs `if hasattr(…)` (QA's D-4). The HTTP test covers the limit, so nothing is missing.
- `settings.py:494`: the off-list refusal says "personal contact details are never shown or opened here". For the new key, the dialog just offered phone and address. `people_fields.py` `NEVER` also still says "nothing here is on either list above" and "never a reader's to browse", but `MANAGER_SEES_FIELDS` now lists five of those fields for a reader. Both comments are stale. ux-learnings (22 Nov, round 2) itself says to change a sentence that a new row makes false.
</details>

---

## AC verification (built scope: "see" only. ACs 31 and 43-48 are deferred by Surbhi)

| AC | State | Evidence (P = proven by my read · R = reported by 03/04, not re-run by me) |
|---|---|---|
| 1 | met in code; phone layout **not verified by me** | P: `can_report` = no own open report and `is_direct_active_report` (hr_api l.1344). D-1 fix: icon is a child of `.sc-topbar` (P). Re-test result not seen |
| 2, 3 | met | P: sheet strings match v4. `send_leaver_report` writes only ToDo. R: status and relieving date read back unchanged |
| 4 | met as drawn; timeout case see m-2 | P: offline words and Try again |
| 5 | **partial** | client half met (P, `s.sending`). Server half not met: M-2 |
| 6, 7 | met, wording differs (m-1) | P: one sentence for no-such, not-yours and self. Refusals go through `access.refuse`. R: log line read from handler |
| 8 | met | P: 31 and 60 inclusive; before joining refused with the 31-day sentence (O-5) |
| 9 | met, wording differs (m-1) | P l.146-150 |
| 10-12 | met | P: plain insert, no reference, so no Comment, `_assign` or DocShare (read in `todo.py`). Last day in Due Date (Q2 approved) |
| 13 | met | P: savepoint and rollback; no queue or scheduler entry in the `hooks.py` diff |
| 14-16, 19 | met | P: `on_employee_update` closes by marker only when status becomes Left. ERPNext refusal leaves the report open (R) |
| 17, 18 | **met as written, not as intended** | rows written (P). Never shown in the portal bell: M-1 |
| 20, 21 | met | P: guard refuses the reporter on validate and trash, and refuses a forged marked insert. Confirmer can close |
| 22-24 | met | P: `open_report_about` returns the reporter's name and date only, for the caller's own record (`my_profile` passes `me.name`) |
| 25, 26, 27 | met | R: QA read matrix, break-tested. P: names escaped in description and bell |
| 28-30, 32-35 | met | P: card hidden unless `get_people_settings` succeeds (System Manager). Role branch and cap in `_set_access_setting`. R: Version row |
| 36-38 | met | P: four fields cut from both readers. `personal_details` re-intersects the closed list and checks the direct Active report. HR gets none (Q3 approved) |
| 39 | met | P: both old throws now go through `refuse` |
| 40-42 | met | P: `lvPersonal` draws only the keys sent, "Not set" for empty. `MANAGER_EDITABLE` untouched (R pin) |
| 49-52 | met | P: grey line from `reported` (one IN query); note; no `relieving_date` write |
| 53-55, 63 | met | R: real-HTTP CSRF, GET 403, 11th refused, break-tested. P: every `except` logs the ID only |
| 56-60 | release steps, not done | OPS-16 dry run, DocPerm reads, ALV-391 state |
| 61 | partial | P: strings wrapped. No Hindi (m-5) |
| 62 | **not verified by me** | D-1 re-test running |
| 64 | met | P: diff has no `deploy/`, DocType, route, queue or scheduler change. No "payroll" on any new screen string (grep) |
| 65 | met | P l.152-154 |

**Prototype v4, screen by screen:** Team card and grey line: match. Scorecard icon: match after D-1 (layout unverified by me). Report sheet, sent message, offline sentence, too-old and too-far sentences: match. Not-yours and duplicate sentences: differ (m-1). Scorecard note: match. Personal details card (last, full width, caption): match. Employee line: match. Administrator card: match for the "see" and role rows; the "change" row is deferred, as approved. Desk ToDo text: match. P-12 timeline: not built, as approved. Outcome lines: drawn in v4 on the Team page, chosen as a bell line in D3, and invisible in the portal (M-1).

## NFR verification

| Budget / dimension | Impact analysis claimed | Code | Finding |
|---|---|---|---|
| Performance | neutral; "+1 indexed query" on My profile | +1 ToDo scan on Team, Scorecard and My profile, **unindexed**; 0 on an ordinary Employee save (P: early return) | neutral if `tabToDo` is small; **not measured** (m-3). 3G timing not measured (OPS-10) |
| Security | improves | ALV-433 cut (P); closed list at both ends (P); forged-insert door closed (P); POST + CSRF + limit (R) | **improves**. Matches |
| Reliability | neutral | one transaction; hooks wrapped; Left dry run on real data not done | neutral; **the double-send claim is false** (M-2) |
| Scalability | neutral | cap of 10 ToDos; one IN query for the team | neutral; the cap is global, not per company (m-4) |
| Maintainability | neutral | ~330 lines in `portal.js`; one new 308-line module | slightly worse, as 03 says; acceptable |
| Data integrity | improves | manager never writes `status` or `relieving_date` (P) | improves; duplicate reports possible under a race (M-2) |
| Compliance / privacy | improves, with ⚠ PRIV-4 | as claimed | improves; PRIV-4 still blocks main |

## Compliance verification

| Obligation | Mechanism in diff | Test | State |
|---|---|---|---|
| Minimisation (SEC-1, SEC-2, PRIV-1) | field cut; `MANAGER_SEES_FIELDS`; `allowed()` at reader; `is_direct_active_report` | E `test_nothing_personal_is_sent_by_default`, Q `TestWhoIsRefusedPersonalDetails` (R, break-tested) | discharged |
| Setting is System-Manager-only with audit (SEC-3, SEC-8) | `ACCESS_GRANTING` + Version row | E `TestSettings` (R) | discharged |
| Refusals logged (SEC-5) | `access.refuse` | E log-handler reads (R) | partial: real on a tenant only where ALV-391 is deployed; D-6 unsettled |
| Notice to the person (PRIV-2) | `open_report_about`, own record only | E (R) | discharged; notice wording still with counsel |
| No leaving fact before confirm (PRIV-3) | no write of `relieving_date` | Q (R, break-tested) | discharged |
| No email, share or comment (SEC-7, SEC-11, OPS-19) | plain insert; "Alert" type | E counts (R) | discharged |
| Retention of the notice (PRIV-4) | none; `on_employee_trash` removes orphans | – | **not discharged; counsel; blocks main** |
| Accountable human | reporter = `assigned_by` on the ToDo (P); confirmer = whoever saves the Employee as Left (`modified_by`; whether Employee keeps a Version row is not checked by me) | – | discharged for the reporter; partial for the confirmer |

## What to delete

- `open_reports_by`'s `user` parameter (unused).
- The duplicate `.lv-icon{flex-shrink:0}` rule.
- If Surbhi takes "Option B" for M-1: both `_tell` calls, `_tell` itself and the one `ignore_permissions` (the ceiling line goes back to 0).
- **A separate line for Surbhi, outside this slice:** `get_employee_detail_for_manager` (`hr_api.py`) and `openEmpDrawer` / `renderEmpDrawer` (`portal.js`) have no live caller. 089 had to edit them for ALV-433. Deleting them would remove a whitelisted endpoint that returns personal data and that nobody uses.

## What was done well

- **Not using `assign_to`, based on reading Frappe's source.** That read found four side effects the spec had not named: the share, the email, the Employee Comment and `_assign`. A plain insert with no reference avoids all four, and break test 4 proves it.
- **The forged-insert door.** The engineer noticed that role `All` can create ToDos and closed the gap with a server-only flag. The spec had not asked for this.
- **Real-HTTP CSRF testing, including the `frappe.in_test` trap** (a minted token is never saved in tests, so a "forged POST refused" test can never pass). That finding is worth adding to the shared context.
- **Closed lists checked at both ends.** A value written straight into `DefaultValue` still shows nothing.

## Confidence

- **Proven:** M-1 (read `notices.py`), M-2 (isolation level read on `alv089-db`, plus the demo output), the DOM suite and the integrity script on HEAD.
- **Reported, not seen by me:** every Python pass count, and the D-1 browser re-measure.
- **Inferred:** that store managers have no Desk access; that `grooming._readable` drops Employee rows.
- **Not checked:** any tenant's ToDo row count, confirmer-role holder count, Custom DocPerm on ToDo, and the set-Left dry run. Those are release reads.

## Subtract pass

On a second read I removed four things from my own draft: a finding about the 480 px rule moving the Joined badge for everyone (it is disclosed and harmless), a finding about the decline path skipping Frappe hooks (it is by design, and 03 already says so), a nit about the ~100-role picker (03 already lists it), and a repeat of the DevOps release gates.

---

## Re-review after round 2 (22 Nov 2026)

**Verdict: SHIP (ready to present for the dev push; not permission to push).** M-1 and M-2 are fixed, and I proved both by test, M-2 by a break test I ran myself. No P0, P1 or P2 is open from this review. Round 2 added three new P3s below. Main is still held by PRIV-4 (06), which this review does not change.

**Where I looked:** worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits` at `3f792c29`, clean. Diff `01b35bae..HEAD`: 9 files, all of them from the slice's own two commits. Nothing came in from anyone else. Bench `alv089-bench` (it mounts this worktree), site `test_site`, DB `alv089-db`.

**I ran (proven):** `run-tests --module` `test_leaver_report_089` gave 43 OK, `test_leaver_report_089_qa` 10 OK and `test_notices_076` 30 OK. `node alvoraa_portal/tests/portal_leaver_report_089_test.js` gave 36 passed, 0 failed. Break test of M-2 with no source edit: I patched `Database.get_values` to drop `for_update` and ran `test_an_overlapping_second_report_is_refused`. As built it passed. Patched, it failed with "PermissionError not raised". No leaver ToDo was left behind (0 open). I did not run `test_portal_security_010`, the Chromium layout test or the integrity script; those figures are the engineer's.

| Item | Result | Evidence |
|---|---|---|
| M-1 outcome bell | **fixed** | `_tell` writes `document_type` "ToDo". `notices.LEAVER` is now part of `OWN_COPY` and `NOTICE_DOCTYPES`. The row is the caller's own (`for_user` filter), so skipping the grooming gate is safe. The feed lists the line, the count includes it in the same single `count` statement, and `mark_all_seen` clears it. The new test calls the real `notices_feed` as the manager and as 4 other people. `inbox_api` counts no "ToDo" Notification Log rows (grep), so the badge does not count it twice. The `test_notices_076` pin was updated on purpose. |
| M-2 double send | **fixed** | `get_values(..., for_update=True)` is a current read under `REPEATABLE-READ` (read on `alv089-db`). The two-connection test is real: it sets the stale snapshot first, then a thread on its own connection commits. It does not test the blocking wait, but the lock on the Employee row already covered that. |
| Timeout words | **better, approval not recorded** | "It may not have been sent... Check your team list before you try again." The advice works, because the Team card shows open reports. But the words differ from prototype v4 and are not in the admin save's form either. The DOM check still calls them "the approved sentence". Owner: Surbhi (prototype parity). |
| Removed `user` parameter | **clean** | Proven by grep: no caller passed it. |
| CSS merge | **clean** | One `.lv-icon` rule. `flex-shrink:0` is kept. |

**New P3s caused by round 2 (proven by reading; impact on tenants not checked):**

- **r2-1 · Deleting an Employee now leaves its outcome lines behind.** Frappe's `delete_dynamic_links` (`frappe/model/delete_doc.py:509`) deletes Notification Log rows by `(document_type, document_name)`. Before this round that matched ("Employee", id). Now the rows are ("ToDo", employee id), so they survive with the leaver's name in the subject until log clean-up removes them. Frappe's `clear_old_logs` defaults to 180 days; I did not check the tenants' Log Settings. Smallest fix: one more line in `on_employee_trash` (`leaver_report.py:321`) that deletes `Notification Log` rows where `document_type` is "ToDo" and `document_name` is `doc.name`.
- **r2-2 · The Desk bell link for these lines is now broken.** Frappe's `get_item_link` (`notifications.js:388-398`) opens `/app/todo/<employee id>`, and no such ToDo exists. Before, the link opened the Employee. This only matters for managers who use Desk. The same one-line fix does not cover it. Setting `link` on the row would.
- **r2-3 · The bell now lists any Notification Log row that a person has about a ToDo**, not just 089's rows. Examples are Frappe's own Mention rows for ToDo comments, and any "System Notification" rule set up on ToDo. They are the person's own rows, so nothing leaks. But their subjects carry `<strong>` tags, and `esc(n.text)` (`portal.js:7988, 8034`) shows those tags as literal text. There are 0 such rows on `test_site`; I did not check the tenants. A filter on `type` "Alert" would narrow this.
- **r2-4 · The locking read scans the whole ToDo table.** `tabToDo` has indexes only on `name`, `creation`, `reference_type` and `reference_name` (read on `test_site`). So the `FOR UPDATE` read locks every ToDo row, and the gaps between them, until the send request commits. Inferred, not measured: every ToDo write on the tenant waits for that request to finish. The wait is short and leaver reports are rare, so this is P3. The index on `alv_leaver_employee`, already waiting for Surbhi (m-3), would narrow the lock to that one person's rows. Owner: DevOps, with m-3.

Still open from the first review, not touched this round: m-1 (duplicate sentence), m-3, m-4 and m-5, plus the nits other than the two fixed here.

**Subtract pass:** I removed a paragraph that restated the engineer's run figures. They are named once, above, as not mine.
