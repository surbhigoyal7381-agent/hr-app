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

## Re-check after fix round 2 (24 Nov 2026)

Read: worktree `.claude/worktrees/086-manager-held-days`, branch `slice/086-manager-held-days`, HEAD `36d701b5`, `git diff 0a181d05..HEAD` and the "Fix round 2" notes in 03. The bench `alv086-bench` runs this worktree's code (md5 of `held_team.py`, `punch_fix.py`, `attendance_correction.py` match, proven). Site `test_site`.

**Verdict: SHIP.** F1 and F2 are fixed. Nothing new found. One honest gap: my own test run was not clean (see "Tests" below), so the green results are the engineer's, not mine.

### Findings

| # | Status | Evidence | Label |
|---|---|---|---|
| F1 blank lines cut the 088 notice | **fixed** | `_file_one` collapses every run of blank lines to one line break before filing (`held_team.py`, the `re.sub(r"\s*\n\s*", "\n", ...)` line). The "One of n" line is still added after a blank line, so it stays out of what 088 prints. A manager can still type a line that reads like "Raised by ...", but it can no longer be a paragraph of its own: 088 prints it as part of the manager's reason, and `owner` and the real stamp stay true | proven in code; pin `test_a_blank_line_in_the_reason_does_not_cut_what_088_prints` read; the engineer's break test (03) not repeated by me |
| F2 bad payload or day gives a traceback | **fixed** | `send_held` wraps `parse_json`; `held_days` wraps `getdate`. Both say a plain sentence with no personal data. The engineer had no break test for the bad `day` line. I ran the unguarded call instead: `getdate("not-a-day")` throws "<strong>not-a-day</strong> is not a valid date string", which does not contain "was not understood". So the pin would fail without the guard | proven by running (the getdate call); pin `test_a_broken_payload_or_day_gets_a_sentence_not_a_traceback` read |

### The `_refusal_of` change (keeps "< and >")

- **It cannot put markup on the screen.** The manager's page never shows a sentence as HTML. Each row's refusal is drawn with `gpEsc(said)` (`portal.js` `hdlRow`, the `hdl-refused` line). A whole-call refusal is drawn with `gpEsc(trErr(e))`. `esc` turns `& < > "` into entities (`portal.js:265-270`). So the screen escapes, whatever the server sends. Proven in code.
- The server-side regex is not a sanitiser, and it does not need to be one. I ran it on test strings: `<<b>script>` comes out as `<script>`, and an unclosed `<img ... onerror=...` passes through. The old `strip_html_tags` was not a sanitiser either. Proven by running. This is safe only because the screen escapes. **P4 note:** the docstring should say so, so nobody later draws this sentence with `innerHTML` unescaped.
- **What can reach a sentence:** our own fixed words; `raise_for_report`'s sentence with the employee's name, which is reached only after the row passed the direct-report check (so only the manager's own report's name); and Frappe's sentences. A row for somebody outside the team gets the fixed `NOT_YOURS` sentence. Proven in code.
- **ALV-436 still works.** `punch_fix.validate` still calls `refuse_if_the_words_would_be_lost` first. `test_reason_rules` sends `<img src=x onerror=alert(1)>` and `<urgent>`. It expects both refused, no request filed, and the full sentence "without < and > around a word". Only the display of the sentence changed. Proven in code; test read.

### M-1 (commit before the day-row lock, duplicate check now a plain read)

- **The scope check cannot be skipped.** In `send_held` the order for each row is: the duplicate-pair check, then `row["employee"] not in team` with `continue`, then `commit`, then `_file_one`. The commit comes after the check, and `_file_one` → `raise_for_report` checks direct report again for every caller (ALV-425). So there are two checks. Proven in code.
- **It cannot file twice.** `_file_one` locks the day row (`for_update`) before the plain duplicate read. Nothing reads the database between the commit and that lock. `nowdate` uses System Settings held in `frappe.local` (`system_settings.py:261-271`, read in the bench). So the duplicate read takes its snapshot after the lock and sees a request another send committed. A day that is not Held, or has no row, is refused, so filing never happens without the lock. Proven in code, with one inference: the "no read before the lock" point rests on the cache being warm. `TheLock` guards it: the engineer's break test shows it fails without the commit.
- Side effect: each row is committed on its own. That was already true after fix round 1 (AC-32). Nothing new.

### Personal data and passwords

- The two new sentences and the new `from`/`to` dates hold no personal data. The Error Log message is unchanged (counts, the manager's id and the fault type). Proven in code.
- No literal password in `test_held_team_086*.py` or `portal_held_team_086_test.js` (grep: the only hits are `seen_token` and `csrf_token: "x"`, a stub). Proven.

### Tests (not clean on my side)

- My run of `test_held_team_086`: 33 ran, 0 assertion failures, **7 errors**. All 7 were MariaDB deadlocks inside the cleanup `_wipe` (`DELETE FROM tabEmployee`, test file line 63), in `TheEmployeeAndHR` and `TheFilerGuard`.
- Another session was running the same module on `test_site` at the same time. I saw its process (`run-tests --app alvoraa_portal --module ...test_held_team_086`) before and after my run.
- So I infer the errors come from two runs clashing on one site, not from the product code. I have not proven that.
- I stopped my two `_proof` runs partway, to stop disturbing the other session. **They may have left test fixtures on `test_site`.**
- I rely on the engineer's results in 03: 33 OK and 11 OK. **Not checked by me.**
- Removes it: one clean run of both modules while no other session uses `test_site`.

### SEC/PRIV status changes since round 1

| Item | Was | Now |
|---|---|---|
| SEC-3 | partial (F2; browser escape on HR's card and the day sheet not tested) | partial. F2 is closed. The browser check on 087's screens is still not run (R3) |
| SEC-5 | met, day-row lock untested | met. `TheDayLock` now exists (I did not run it cleanly). R2 is closed if that test passes |
| SEC-8 | met, see F1 | met. F1 is closed |

Every other SEC and PRIV item is unchanged.

Subtract pass: I removed a planned table of every changed line (the diff has it) and a repeat of the round-1 threat model.
