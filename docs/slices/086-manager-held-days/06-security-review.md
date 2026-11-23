---
slice: 086-manager-held-days
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-23
read: worktree /Users/mac/hr-app/.claude/worktrees/086-manager-held-days, branch slice/086-manager-held-days at eb8f781f, diff 412d5361..HEAD
ran on: stack alv086-bench, site test_site
risk tier: 1
---

# 086 - Security review

**Verdict: SHIP WITH FIXES.** No stop-the-line finding. No Blocker, no Major. Two Minor findings (F1, F2) are small and worth fixing before main; the rest are notes.

**Governance.** I wrote this slice's `01c` too. The technofunctional reviewer should check SEC-1 and SEC-7 on their own (lesson 6).

## 1 · Requirements

| Req | Status | Mechanism in the diff | Proof | Label |
|---|---|---|---|---|
| SEC-1 scope per row, every caller | **met** | `held_team.py:36-42` (`_team`: Active Employee + switch + `_reports_to(me, deep=False)`, which filters `reports_to = me` and `status = Active`, `attendance_analytics.py:106-112`); per-row check `held_team.py:174-178` with one fixed sentence and `access.log_refusal`; D-1 removes the `_may_review` skip in `raise_for_report`, `attendance_correction.py:2488-2499` | `test_the_seven_case_scope_test` (5 strangers, 5 security lines read from a fresh process, no name in the answer); `test_hr_and_a_submit_right_login_are_held_to_direct_reports_too`; `test_a_manager_who_has_left_or_a_tenant_switch_off_files_nothing`; proof `test_a_colleague_a_stranger_and_a_guest_get_nothing_from_either_call`; break test in 03 | proven (code + tests). **Test gap:** no row for "another company's person" and no Shift Supervisor login; the code has no branch for either (membership is `reports_to = me`, whoever calls), so inferred covered |
| SEC-2 every row through `raise_for_report` | **met** | `held_team.py:267`; no `ignore_permissions` and no `frappe.flags` in the module (grep: 0; all 11 added `ignore_permissions` are test fixtures) | `test_this_module_never_ignores_permissions`, `test_a_partial_send_leaves_no_document_for_a_refused_row` | proven |
| SEC-3 fixed shape, cap 50, reason escaped | **partial** | Only the five `KEYS` are read (`held_team.py:31, 155-157`); 51 rows refused before anything runs (`:146`); duplicate pair (`:169-172`); 500 characters (`:234`); manager page escapes with `gpEsc` (portal.js `hdlRow`) | `test_shape_and_size_refusals`, `test_reason_rules` (Frappe strips `onerror` on save), proof fifty-rows test | proven for the server. **Not tested:** the browser test of a script reason on HR's card and the employee's day sheet (087 screens). Malformed payload: see F2 |
| SEC-4 POST, CSRF, 30 an hour | **met** | `@frappe.whitelist(methods=["POST"])` + `_limited(SELF_KEY, "user", 30, 3600)` (`held_team.py:135-136`). The limiter keys on `frappe.session.user`, set by the wrapper over anything the client sends (`field_app_limits.py:78-80`), and Frappe's key adds the method path (`frappe/rate_limiter.py`, read in the bench). So no argument can move the caller to a new bucket | 04 row 18, over real HTTP: GET 403, Guest 403, signed-in POST without the CSRF header 400 `CSRFTokenError`, 0 filed; proof `test_the_thirty_first_send_in_an_hour_is_refused`. `ignore_csrf` not set in test_site or common config (grep) | proven by the test engineer's run; limiter key read by me |
| SEC-5 replay / double send | **met** | Locking reads of the day row and the open request (`held_team.py:242-247`); rows sorted so locks are taken in one order (`:159`) | `TheLock` two-connection test (break test in 03 fails without it); deadlock proof test green after fix round 1 | proven. Day-row lock has no test of its own (temporary debt, 03) |
| SEC-6 case A on counsel's word | **met (case A)** | 087's one condition in `_own_the_confirm_fields`; 086 sends no confirm key. Case A rests on counsel's answer of 21 Nov **as relayed by Surbhi** (02 §0.3); I have not seen counsel's text | `test_case_a_holds_only_for_the_managers_plain_addition`, `test_the_request_needs_no_confirm_and_hr_approves_it` | proven in code. Counsel's third condition (ALV-426, notice on the register) is the release gate OPS-63: 088 switched on first |
| SEC-7 no change or delete by the filer or the employee | **met** | `punch_fix.py` `_refuse_edit_by_others` (on `CONFIRMED_CONTENT`, keyed on `before.owner`) and `refuse_delete_by_others` via `hooks.py` `on_trash` | `TheFilerGuard` (4 tests, break tests in 03). **My own probe, run on test_site:** as the manager, `frappe.client.set_value(..., {"owner": employee login})` to make the request look like the employee's own, then edit, then delete. Frappe refused the owner change (`CannotChangeConstantError`), the edit and the delete were refused by the new guard, time and stamp unchanged. Probe file deleted after the run | proven by running |
| SEC-8 rebuilt a year later | **met** | Stamp now carries the manager's id (`attendance_correction.py:2541-2544`); "One of n" after a blank line (`held_team.py:266`) | proof `test_the_request_alone_says_who_filed_for_whom_in_which_batch_and_who_decided`; `test_the_notice_for_the_register_carries_only_the_managers_words` | proven. See F1 |
| PRIV-1 five keys, nothing else | **met** | portal.js send builds `{employee, date, time, in_or_out, reason}` per row; no shared reason | DOM test `portal_held_team_086_test.js` (payload of the real Send button) | proven by test |
| PRIV-2 reason goes nowhere new | **met** | Answer holds `employee, date, ok, request` or a sentence (`held_team.py:164-211`); Error Log message is counts + manager id + fault name only (`:207-210`); `log_error` with a message stores that message, not a traceback with locals (`frappe/utils/error.py:61-68`, read) | `test_the_answer_holds_no_reason_and_no_punches`, `test_an_unexpected_error_is_a_sentence_and_the_log_holds_no_reason`, `test_no_email_and_no_notification_of_its_own`, proof marker test | proven. Sentry capture not checked (not configured, inferred) |
| PRIV-3 what the list shows | **met** | `_shaped` returns name, date, shift times, punch time/minute/source label and `single_is_out` (`held_team.py:111-125`); `_source` is a label only (`punch_fix.py:598-599`) | `test_only_direct_reports_with_no_open_request_and_nothing_sensitive` (no user_id, email, latitude, longitude, image, photo) | proven |
| PRIV-4 nothing on a shared phone | **partial** | Values live in `hdl.vals` in page memory only (portal.js) | DOM test: both stores empty. Back-after-logout test not run (04) | proven for storage; Back not checked |

## 2 · Findings

**F1 · Minor (P3) · a blank line in the manager's reason cuts what the employee's notice prints.** `send_held` keeps the reason as typed (`held_team.py:263`); 088 prints only the text before the first blank line (`punch_fix._reason_of`, `punch_fix.py:609-611`). Scenario: a manager types "Left at 20:30", a blank line, then more; HR's card shows all of it, the employee's monthly notice (counsel's ALV-426 condition) shows only the first paragraph. The same gap lets a manager type a paragraph that looks like a second "Raised by ..." stamp; `owner` stays the true filer. Fix: collapse blank lines in the reason before filing (one line in `_file_one`; the single door `raise_for_report` has the same gap and could take it instead). Label: inferred from code, not run.

**F2 · Minor (P4) · a malformed payload may give a traceback, not a sentence.** `frappe.parse_json` on a bad `rows` string (`held_team.py:143`) and `getdate(day)` on a bad `day` in `held_days` (`:81`) are not caught. SEC-3 asks for a sentence. Nothing is filed and nothing leaks. Label: inferred from code, not run.

**Notes (P4, no action needed):** a repeated stranger row gets "Already waiting with HR" instead of the scope sentence, because the duplicate check runs first (`held_team.py:169-178`); it reveals nothing. `onclick` attributes put HTML-escaped employee ids inside JS strings (`hdlRow`); safe today because ids come from HR's naming series, an existing pattern.

**Checks with nothing found:** commit-per-row cannot file a row that skipped the scope check (scope at `:174`, savepoint and commit only after `_file_one` returns at `:179-185`, and `raise_for_report` checks again). No literal password or key in the new test files (grep for password/secret/api_key/token; gitleaks itself not run locally). No new public route, cache, export, field or job.

## 3 · Obligations

DPDP baseline entries were last verified 24 Aug 2026, now stale (more than 90 days). I did not re-verify them in this review; no requirement here turns on their exact text. They must be re-checked before anyone quotes them to a customer.

## 4 · Residual risk (proposed; owner Surbhi; nothing accepted until she says so)

| # | Risk | Label |
|---|---|---|
| R1 | A manager files a false later time for a friend; under case A only HR's look at the punches stands in the way (01c A1) | intentional trade-off, counsel's case A |
| R2 | Day-row lock has no test of its own | temporary debt; removed by a test or by dropping the lock |
| R3 | Browser escape test on HR's card and the day sheet not run; PRIV-4 Back test not run | temporary debt; removed by the two browser checks |
| R4 | `security.log` keeps about 2 MB; probes are visible only for a short time | acceptable simplification (01c SEC-8) |

Subtract pass: I removed a planned section restating the threat model (it is in 01c) and a table of every test name (04 has it).
