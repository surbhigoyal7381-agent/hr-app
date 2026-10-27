---
slice: 063-dtc-leave-credit-and-lwp - the Housekeeping leave days part
artifact: 06b-security-verification-housekeeping (Tier 1)
author: hrms-security-privacy-engineer
date: 2026-10-27
branch: slice/063-housekeeping-leave, tip f65227a9, on origin/dev ba974baf (5 commits)
requirements: 01c revision 4b (24 Oct 2026). **It is not in git.** It exists only as an uncommitted edit in the worktree `067-pay-slip-marks` (finding M-3)
method: code read of the whole diff, plus the Frappe source in `hrlocal-bench` (read only). **I did not run any test.** Test results quoted below are the engineer's (05-implementation-notes-housekeeping.md section 4), not mine
---

# 063 Housekeeping leave: security and privacy verification

**I wrote 01c, including SEC-18, SEC-19, SEC-20 and PRIV-7 (lesson 6).** This review checks my own
requirements. Someone else should read section 2 rows SEC-18 to SEC-20 again.

## 0 · Verdict

**No blocker.** Nothing in this build lets a person see or change something they should not, and
Housekeeping pay does not move.

The one real hole is old: **F-3 is still open in code.** An HR user limited to one branch can still
open another branch's person through `get_leave_summary`, and see their leave reasons. The new days
figure is guarded; the rest of that reply is not. It is not live at DTC today. It should be fixed
before anyone at DTC is given a Branch permission.

| # | Rank | Urgency | One line |
|---|---|---|---|
| M-1 | **Major (old, not caused by this build)** | P2 - fix or accept in writing | F-3: an HR user in another branch gets the person's leave list, with reasons, from `get_leave_summary` |
| M-2 | Minor | P3 | "DTC" is written in 4 on-screen strings and 1 engine note. SEC-15 asks for no company name in code |
| M-3 | Minor | P3 | 01c rev 4b, and the other papers this build follows, are not committed anywhere |
| M-4 | Minor | P3 | 01c is behind three of Surbhi's later decisions (HR sees days on behalf, HR is told, list two's keys) |
| M-5 | Minor | P3 | Two release checks are still not done: SEC-17 on DTC, and a second person checking the table rows (SEC-19) |
| M-6 | Minor | P4 | Two test gaps: no slip test with an approved Paid Leaves day for a table person; no table-person version of SEC-1 (d) |
| M-7 | Minor | P4 | SEC-18 is keyed on "category earns no leave credit", not on "Contract". The same at DTC if Contract is the only such category. I could not check DTC |

## 1 · Tries to break it

| Try | Result | Label |
|---|---|---|
| HR user limited to branch South asks for a North person's **days figure** | Refused. `types_offered` adds `left` only if the person is inside `permitted_employee_filters()` (company and branch), `leave_rules.py:763-765`. The preview and apply paths go through `_leave_subject`, which checks the branch, `hr_api.py:2517-2521` | Verified in code. The engineer's tests `test_hr_in_another_branch_gets_no_figure` and `test_hr_in_another_branch_sees_no_figure` use a real Branch User Permission (fixture "Anil"), so they can see it |
| The same HR user asks for **anything else** about that person | **Not refused.** `get_leave_summary` uses `_hr_target_employee`, which checks the company only (`hr_api.py:2299`). The reply holds the last 10 Leave Applications with `description`, the reason (`hr_api.py:2334-2343`), the balances, `lwp_in_play`, and the new `no_paid_class` (`leave_rules.py:770-771`) | Verified in code. The test at `test_leave_063_rules.py:370` calls it as Anil and gets a reply rather than a refusal, which shows the call goes through. M-1 |
| A plain employee asks for another person's figure | Gets their own. `get_leave_summary` ignores `employee_id` for a non-HR caller (`hr_api.py:2309-2312`). The card is built only when `own` (`hr_api.py:2350, 2356-2357`). `preview_leave_request` refuses `on_behalf_of` for a non-HR caller (`hr_api.py:2514-2516`) | Verified in code. No table-person test for it (M-6); the path is the same for every person |
| The new HR notice leaks free text | No. Body is name, dates, number of days and two fixed sentences, each through `escape_html` (`leave_rules.py:290-295`). No type, no reason, no approver. Same subject as the chain notice. A Notification Log subject is cleaned by Frappe's `_sanitize_content` on insert (`frappe/model/base_document.py:1307-1347`), and the name fields are now HR-only (ALV-215, `employee_field_rights.py:40-44`) | Verified in code. The engineer's test puts `SECRET-REASON-063` in the reason and checks it is absent (`test_hr_in_scope_are_told_of_every_approval_once_with_the_same_four_facts`) |
| The HR notice reaches the wrong HR | No. `hr_users_in_scope` asks `permitted_employee_filters(u)` for each HR user (`leave_rules.py:347-366`). Anil (other branch) is not told, by test | Verified in code |
| Someone edits the new child table who should not | No. `Alvoraa Leave Credit Row` has no permissions of its own, so it follows the parent. The parent: System Manager writes; HR Manager reads only; HR User nothing; `track_changes` 1 (`alvoraa_payroll_rule_set.json`). Frappe saves a child row only through its parent | Verified in code. Test `test_hr_reads_the_table_but_cannot_change_it`, and a Version row test |
| An employee moves themselves onto the table by editing `designation` | No. `designation` and `employment_type` are level 2, HR-only (`employee_field_rights.py:40`), and every field a rule set names is locked too (`rule_set_fields`, line 125) | Verified in code. **Whether this is applied on DTC is not checked** (M-5) |
| Housekeeping pay changes | No. Before: a Contract person earned 0 credit, so `paid_days = day_credits`. Now: the table credit is reported but `paid_days = day_credits + 0` for a table person (`payroll_month.py:239`); `leave_encashed` stays 0 (`226-232`). No money field reads the credit. No Additional Salary is made from it. Contract earns no marks | Verified in code. Engineer's tests: `test_the_credit_is_never_paid` (net equal with and without the table), and real draft slips: 26 days worked gives `payment_days` 26, no Additional Salary, same with the rows deleted |
| New JS writes text without escaping | No. Every string in `lpRenderTableCard` and the new sentences goes through `gpEsc`. The two raw values are `lpNum(...)`, which always returns a number (`portal.js:6880`) | Verified in code |
| New `ignore_permissions`, `allow_guest`, endpoint, cache, raw SQL, delete or purge | None in the diff. `hr_api.py` and `hooks.py` are untouched | Verified in code (diff scan) |

## 2 · Requirements

"Unchanged" means the diff does not touch the code behind it. I read the diff to confirm that; I
did not run the tests again.

| Req | Status | Mechanism | Test |
|---|---|---|---|
| **SEC-1** list two (table card, days only, no `to_be_paid_out`) | **Verified** | `CARD_KEYS_TABLE` `leave_rules.py:58`; every key named in `_table_card` 647-688; `prepare(..., employee=)` line 558 | `test_the_keys_are_list_two_exactly` (key equality); `test_no_pay_figure_reaches_the_card` (no 12000, no pay names). Note: the list has 9 more keys than 01c's list two, none about pay (M-4) |
| SEC-1 (c) HR gets no card | **Verified** | `hr_api.py:2350-2357`. Surbhi's A-1 / Q-S2 now let HR see the days **left** on behalf; that is not the card | `test_hr_on_behalf_sees_the_days_left_but_not_the_card` |
| SEC-2 nothing when the rule set is off | **Verified, unchanged** | `rule_set_for` gate, `leave_rules.py:748-753`, `776-786` | Existing 063 tests |
| SEC-3, SEC-6, SEC-7, SEC-8, SEC-12, SEC-13, SEC-16 | **Unchanged** | Not touched by this diff. SEC-7's branch check is the reason preview and apply are safe on behalf | Existing modules re-run by the engineer (43, 17, 12, 9, 11 OK) |
| SEC-9 no new `ignore_permissions` | **Verified** | None added. The new `frappe.get_all` on Attendance in `_table_card` filters on the server-resolved `emp.name` | Diff scan |
| SEC-10 pay arithmetic | **Verified for the office path, unchanged** | `test_an_office_call_is_unchanged`; office slip 26 + 4 = 30 | Engineer's run |
| SEC-11, SEC-14 | **Not verified** | Release and rehearsal steps. The rehearsal scripts were not extended (engineer's held list) | - |
| **SEC-15** one DTC check, no name in code | **Logic verified; wording not met** | Every new path asks `rule_set_for`. The designation is read from the rows, never written in code (no "Housekeeping" value in any non-test file). But "DTC" is in `portal.js:6995, 7302, 7374` and `payroll_month.py:202` (M-2) | Diff scan |
| SEC-17 field rights | **Verified in code; not verified on DTC** | ALV-215 on dev | Release check not done (M-5) |
| **SEC-18** who the table reaches | **Verified, with one difference** | `credit_rows_for`, `payroll_slip.py:78-93`: rule set on, category earns no credit, rows for the designation, class > 0, 28-31 day period. Class caps the row (`payroll_month.py:189-204`). Condition 2 is "category earns nothing", not "employment type is Contract" (M-7) | (a)-(g) all present in `TestWhoTheTableReaches`; Permanent person keeps office rule; rows deleted gives 0 |
| **SEC-19** table cannot be saved wrong | **Verified in code; second-person check not done** | `_check_credit_rows`, `alvoraa_payroll_rule_set.py:255-306`: backwards, negative, not starting at 0, overlap, gap, falling, short last row. Designation existence is Frappe's own link check (inference). Version row | 7 refusals, a valid table saves, an empty table saves, HR cannot write, Version row. Every row edge in `test_payroll_month` |
| **SEC-20** a table credit never becomes DTC pay | **Verified** | `payroll_month.py:226-239`; no Additional Salary path reads it | (a)-(e) present: card payload, slip `payment_days`, no Additional Salary, same with rows removed, office staff still credited |
| PRIV-1 chain notice | **Verified; changed slightly** | The approver is no longer told their own approval (`leave_rules.py:271-273`). Fewer recipients, same four facts | Existing + new tests |
| PRIV-1 / N-1b HR told of every approval | **Verified** | Same subject, same facts, branch-scoped HR, once each (`285-295`). Surbhi's decision 25 Oct; **not in 01c** (M-4) | 4 new tests |
| PRIV-2 team surfaces | **Unchanged** | - | - |
| PRIV-3 no copy of the figures | **Verified** | No cache, no stored figure, no export. The one new DocType holds rule rows, no person | Diff scan |
| PRIV-5 no personal content in errors | **Verified for the card; worry for the preview** | Card wrapped, Error Log title has the employee id only (`leave_rules.py:583-588`). The preview calls the engine unwrapped (worry W-1) | Existing card test |
| PRIV-6 no retention change | **Verified** | No delete, purge or retention code | Diff scan |
| PRIV-7 agency gets its own people, days only | **Verified that nothing is built** | No export, report or email to an agency. Point 3 (do not send the desk report) is still only an instruction (W-3) | Review rule |

## 3 · Findings, in full

**M-1 · Major (old) · P2 · F-3 is open: branch-limited HR can read another branch's leave reasons.**
*Who, how, what:* an HR User whose User Permission limits them to branch South calls
`hr_api.get_leave_summary(employee_id=<a North employee>)`. `_hr_target_employee` checks the company
only (`hr_api.py:2299`), so the call goes through. The reply carries that person's last 10 Leave
Applications with `description` (the reason, which can name an illness), read with
`ignore_permissions` (`hr_api.py:2334-2343`), plus balances and `lwp_in_play`. This build adds one
small key to that reply (`no_paid_class`, the class name), and guards the one figure it was asked to
guard.
*Why it matters more now:* the 42 Housekeeping staff have no logins, so HR files all their leave on
their behalf. That makes giving a branch HR person a Branch permission more likely.
*Not live at DTC:* 0 of 7 HR users had a Branch permission on 21 Oct 2026. I could not re-check that
today.
*Smallest fix:* in `get_leave_summary`, apply the same `permitted_employee_filters()` check
`_leave_subject` already has (`hr_api.py:2519`). It is one check, and it touches `hr_api.py`, so it
needs its own approval. Owner: `hrms-fullstack-engineer`. Surbhi decides: fix now, or accept in
writing until the first Branch permission is made.
*Debt label:* temporary debt; removed by that one check.

**M-2 · Minor · P3 · "DTC" in code.** `portal.js:6995, 7302, 7374` and the engine note
`payroll_month.py:202`. The logic does not depend on it. On any other tenant with a table, the
screen and the HR report would name DTC. The engineer raised it as N-7. "Your company" would be safe.
Surbhi's call.

**M-3 · Minor · P3 · The requirements are not in git.** 01c rev 4b, 01f, 01g, spec v4 and strategy
v2 exist only as uncommitted edits in `.claude/worktrees/067-pay-slip-marks`. If that worktree is
cleaned, the record of what was required is gone. Commit them.

**M-4 · Minor · P3 · 01c is behind Surbhi's later decisions.** A-1 / Q-S2 (HR sees days left on
behalf), N-1b (HR told of every approval) and N-8 (approver not told) are hers, of 25 Oct and 27 Oct,
and are not in 01c. List two in code has 9 non-pay keys more than 01c's list two (`housekeeping`,
`attended_up_to`, `used_dates`, `waiting_from`, `approver`, `month_length`, `rows`, `lwp_in_play`,
`lwp_limit`) and no held-day keys. None carries pay or another person. I own 01c and will update it
when asked; I did not change it here.

**M-5 · Minor · P3 · Two release checks still open.** (1) SEC-17: confirm on DTC that `designation`,
`employment_type` and the rule set's fields are at level 2. Without it, the table can be reached by a
self-edit. (2) SEC-19: a second person checks the ten rows against DTC's document (gate G-A3). Both
are already gates; they are listed so nobody reads this review as clearing them.

**M-6 · Minor · P4 · Two test gaps.** (a) No slip test with an approved Paid Leaves day for a table
person. The code clearly gives it 0 paid days, but `test_used_is_the_approved_paid_leaves_up_to_earned`
does not assert `paid_days`. (b) SEC-1 (d) is not repeated for a table person. The path is the same.

**M-7 · Minor · P4 · SEC-18 condition 2.** The code reads "the person's category earns no leave
credit" (`payroll_slip.py:88`), not "employment type is Contract". This is the same at DTC only if
Contract is DTC's only category with `earns_leave_credits = 0`. *Inference*; I could not check DTC.

## 4 · Worries (I cannot yet write "this person, this path, sees this")

- **W-1** The preview (`leave_rules.py:888`) calls the engine without the try/except the card has. An
  engine error gives HR a raw error. Frappe sends no local values in it, so I see no figure leaking.
- **W-2** `hr_users_in_scope` checks only that the User is enabled. A departed HR person whose login
  was never disabled (lesson 3), and who has a Company User Permission, keeps getting the new HR
  notices. The helper is old; this build gives it a new use.
- **W-3** The desk report's "why" note now says "Reported to the agency". That may invite HR to send
  the report to agencies. The report has rupees for everyone (PRIV-7 point 3), and nothing stops it.
- **W-4** The slip hook still fails open (01c section 11). Housekeeping can now have approved Paid
  Leaves days, which Frappe's own arithmetic would pay if the engine failed. Not live: DTC runs
  payroll outside the portal (27 Oct scope split).

## 5 · What I could not check, and what I would need

- **Any test run.** I ran nothing. Results above are the engineer's. To check myself I need my own bench
  (containers `hrlocal-063s`, site `test063s`, ERPNext setup) and about half an hour.
- **DTC data:** the Branch permission count today, the field levels, the category settings, who holds
  HR roles. That needs a read-only query on dtc.alvoraa.co, with Surbhi's word.
- **A real browser** for the new card.
- Baseline obligations: last checked 24 Aug 2026, 64 days ago, inside the 90-day rule. This build
  engages no new obligation.

## 6 · Residual risk

| Risk | Kind | Level | Who accepts | Date |
|---|---|---|---|---|
| F-3, branch HR reads another branch's reasons (M-1) | Temporary debt | P2 | **Surbhi - to decide** | open |
| Rows typed wrong pay nothing but report wrongly to an agency for up to 36 people (SEC-19) | Removed by the second-person check, gate G-A3 | P3 | Surbhi (gate) | open |
| PRIV-7 point 3 enforced only by instruction (W-3) | Intentional trade-off until Q11 | P3 | **Unowned** | open |
| "DTC" in strings (M-2) | Acceptable simplification if Surbhi keeps the wording | P4 | Surbhi (N-7) | open |

Nothing here is dangerous debt while the rule set stays off at DTC.

## 7 · Subtract pass

Removed on the last read: a row-by-row restatement of the engineer's test list (it is in 05); a
finding about notification subjects being rendered raw in Frappe's bell (Frappe cleans them on save,
and the name fields are HR-only now, so it is not a finding); a note on query counts (DevOps's area,
and within budget).
