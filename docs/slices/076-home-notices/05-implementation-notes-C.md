---
slice: 076-home-notices
artifact: 05-implementation-notes-C (Part C, expenses from Pending, and birthdays)
author: hrms-fullstack-engineer
date: 2026-10-29
status: built and tested LOCALLY on branch slice/076-part-c (worktree .claude/worktrees/076-part-c), in my own container hrlocal-076c on my own sites test076c, test076cs and test076cl. Not pushed. No server, shared bench, dev or production site touched.
tier: 1 (money and personal data). Plan: 04-impact-and-strategy.md, Part C, and Surbhi's decisions in 01b.
---

# 076 Part C: expenses from Pending, and birthdays. Implementation notes

## Bad news first

1. **Two release blockers, both outside the code.**
   - **DTC's expense approvers are unknown.** Her decision 4 means a portal claim with no approver is now **refused** ("Ask HR to set your approver."). If DTC staff have no expense approver on their Employee record and none on their Department, every portal expense claim at DTC is refused from the day Part C goes live. Someone with access must count, read-only, the active DTC employees with neither, before Part C goes to production. HR fills them first if the number is large.
   - **Counsel's written note on birthdays is still missing.** Counsel agreed orally. The birthdays switch ships **off** on every tenant and must stay off until the written note arrives (01c risk 3, accepted 28 Oct on that condition).
2. **An approver needs the "Expense Approver" role to decide, in the portal or in Desk.** The claim's approval status is a protected field (level 1) in Frappe HR. Frappe HR gives the role automatically to anyone saved as an Employee's expense approver. **A Department-level approver may not have it.** Such a person sees the claim in Pending, but Approve is refused with "Your login cannot approve expense claims yet. Ask HR to give you the Expense Approver access." I did not add `ignore_permissions` to get round it (SEC-14 forbids it). The DTC count above should include "approvers without the role".
3. **Part A's real-browser balance check never fed the Pending and Notices cards.** Its fake server matched calls by the last part of the address, but the two cards ask with the full dotted name, so both cards were always drawn empty. Part A's "45 cells, 0 failures" was true for the grid but not for full cards. I fixed the fake server (one line) and re-ran all 90 cells with full cards (section "Real-browser balance check").
4. **A colleague can read another person's date of birth through Frappe's own API if their login has no Employee User Permission.** ERPNext adds that permission when a login is linked on the Employee form; a login linked by a script or a direct database write has none. This is not caused by Part C (field rights were not changed), but the birthdays card makes the dates more interesting. My test adds the permission the way real data has it. **Worth a read-only check at DTC:** logins with an Employee record but no Employee User Permission.

## What I built, file by file

| File | What | Rung, and why not lower |
|---|---|---|
| `alvoraa_portal/hr_api.py` | `apply_expense_claim` sets `expense_approver` (the Employee's, else the Department's first, the lookup Frappe HR's own form uses) and refuses with no approver (decision 4). New `expense_approver_for(employee)` (used by filing and the backfill). New `decide_expense(name, action, reason)`. `get_expense_claims` adds `decline_reason` to the caller's own claims. | 4. Frappe HR's filing in the portal set no approver, so nobody's Pending could ever show a claim. No Desk path works on a phone. |
| `alvoraa_portal/inbox_api.py` | New part `expense_approvals` after leave: Draft, undecided claims where the caller is the named approver, never their own; `get_list`; cap 50; count equals rows. Keys exactly `name, employee_name, expense_type, expense_date, amount, note, waiting_since, action`. Added to `PARTS`, `APPROVAL_PARTS`, `ROW_KEYS`, `parts()`. | 4. Same contract as the other six parts. |
| `alvoraa_portal/home_people.py` (new) | The three Custom Fields; `birthdays_this_month(see_all)`, `set_birthday_hide(value)`, `birthdays_switch_state()`, `set_birthdays_switch(value)`; `keep_hide_birthday` (Employee validate). | 3 for the fields, 4 for the endpoints. No new DocType. |
| `alvoraa_portal/hooks.py` | Four lines, each added at the end of its list: Expense Claim `before_submit: refuse_own_submit` (SEC-13); Employee `validate` gains `keep_hide_birthday` (the existing entry is kept); `home_people.after_migrate` in `after_migrate` and `after_install`. | 3. Same hook Leave Application, Attendance Request and Grooming Mark already carry. |
| `patches.txt` + `patches/v1_0/expense_claim_approver_backfill.py` | Open Draft claims with no approver get one, through `doc.save` so Frappe HR makes its share. Prints "set N, unresolvable M"; names nobody; a claim that will not save is counted and left alone; a second run does nothing. On test076c: "set 0, unresolvable 0" (no claims there). | 4 (AC-79). |
| `templates/includes/ess/parts/home.html` | The Birthdays card (after Leave balance, as drawn), hidden until the server says the switch is on. The My profile panel. | markup |
| `templates/includes/ess/parts/org-settings.html` | The "Birthdays and anniversaries on Home" switch card, shown only when the server answers (HR Manager, System Manager). | markup |
| `templates/includes/ess/frame.html` | "My profile" in the phone account menu; on a laptop, the name at the bottom of the sidebar opens My profile (it is a keyboard-reachable button). | markup |
| `public/js/ess/portal.js` | Pending: expense rows ("Expense claim · ₹2,300 · Travel · waiting 8 days", Review), the CXO row "Expense claims", `hmExpenseSheet`, and `hmDecide` now also sends expense decisions (through `gpFetch`, so a refusal comes back in the server's own words). New `bd`/`mp`/`bs` block: Birthdays card and See all, My profile tick, the switch with the confirm before switching off. Claims screen: "Declined: <reason>". One line each in `loadHome`, `switchPanel` and the Home click handler. Nothing moved or re-indented. | 4 |
| `public/css/ess/panels.css` | 15 lines at the end of the 076 block: static rows, the amount, the switch, the reason line. Tokens only. | CSS |
| Tests | New `tests/test_expense_birthdays_076.py` (30), new `alvoraa_portal/tests/portal_expense_birthdays_076_test.js` (56 checks, registered in `run_dom_tests.js`, 18 to 19). Changed on purpose: `test_home_076` (the part list now has `expense_approvals` second), `test_expense_and_scoping` (its claimants get an approver, as real data must now have), `test_frame_endpoint_registry_034` (one declared `frappe.get_all`: the first line of the claims on the page). `measure_076.py` gains an `after_c` set. `scripts/browser_check_home_076.js`: birthdays on and off, expense rows, and the fake-server fix (bad news 3). | |

Not touched, and why: `subscription.py` and `translations/en.csv` (no new DocType in Part C); `employee_field_rights.py` (the opt-out field stays at level 0, so the person's own record shows it; `keep_hide_birthday` is what stops anyone else changing it); `access.py`; `hrms-employee.html`; `deploy/`; `.github/`.

## How each rule is enforced on the server

| Rule | Where |
|---|---|
| Only the named approver decides (SEC-12) | `decide_expense`: the claim is read with a row lock first; refused unless `expense_approver` is the caller and the caller has an Active Employee record. A guessed or missing claim id gets the same refusal, so it does not say whether the claim exists. Each refusal is logged by `refuse()` with the claim id and the rule, never a name or an amount. |
| Nobody decides their own claim, on any door (SEC-13) | `refuse_own_decision` in `decide_expense`, and `refuse_own_submit` on Expense Claim `before_submit` for Desk, REST and imports. Holds with HR Settings `prevent_self_expense_approval = 0`. |
| A decision happens once, through Frappe (SEC-14) | Row lock, then "Draft and undecided" or "This claim has already been decided."; `approval_status` set, then `doc.submit()`. No `ignore_permissions`, no `db_set`, no `set_value`, no raw SQL (a test reads the function's source). Frappe HR posts the ledger on approve and zeroes the sanctioned amount on decline. |
| The decline reason is safe and private (SEC-15) | 1 to 140 characters after trimming; stored HTML-escaped in `alvoraa_decline_reason` (so Desk shows it as text, the lesson from Part B's review); unescaped only in the claimant's own `get_expense_claims`; the page escapes it again. `remark` (the claim's title) is never written. |
| Amounts reach only the approver (SEC-16, SEC-19) | The part filters on `expense_approver = caller`; `get_list`; fixed key list; `no_rows()` for a caller with no Active Employee. |
| No year or age leaves the server (PRIV-5) | `_month_rows` reads the two dates on the server, in one query-builder query, and each row is built from a fixed key list: name, kind, day, month (+ years). |
| Switch and opt-out on the server (PRIV-6) | Switch off: `{"on": 0}` before any Employee query (a test counts the statements). Opt-out excluded inside the SQL. `set_birthday_hide` takes no employee argument. Any other save of the field is put back by `keep_hide_birthday`. Only HR Manager or System Manager reads or changes the switch; the change is saved through the HR Settings document, so its Version row is "Last changed by". |
| Same company and branch, Active only (PRIV-7) | The viewer's own Active Employee gives company and branch; no branch or no Active Employee gives an empty list without a query on colleagues. |

## Surbhi's decisions applied

- **Decision 4** (overrides spec AC-78): no approver means the claim is refused with "Your expense claim could not be filed because nobody is set to approve it. Ask HR to set your approver." The filing pop-up shows these words (it already shows the server's own refusal text).
- **Decision 2, option (a):** a small "My profile" screen with only the tick, opened from the account menu.
- **Decision 5:** the tick says "on Home".
- **Q2 working default:** the switch ships off; the field's default is an explicit 0.
- **Q4 working default:** only the named approver decides in the portal.

## Prototype parity (02-design.md section 14, the Part C rows)

| # | Drawn feature | Built as drawn? |
|---|---|---|
| 9 | Expense sheet: name, "Expense claim", amount large, type and date, note, "Waiting N days. Approving passes it to accounts for payment. You cannot take it back here.", Approve / Decline, "Why are you declining? Pooja will read this.", "Send decline", both toasts | yes |
| (Pending) | Expense row "Expense claim · ₹2,300 · Travel", "waiting N days", Review | yes |
| 10 | "Declined: <reason>" on the employee's claims screen | yes (not drawn; spec words) |
| 18 | Birthdays card: initials, name, "Birthday" / "Work anniversary · 5 years", "Today" or "29 Oct", "earlier this month", 5 rows, "Showing 5 of N", "See all N", the sheet "Birthdays and anniversaries, October" with "Only people in your own branch who share their dates.", both empty sentences, the cake icon | yes |
| 19 | Absent when the switch is off, grid reflows | yes |
| 20 | My profile tick, hidden when the switch is off ("There is nothing to set here right now."), the two toasts, the "Organisation settings" button for HR | yes, with "on Home" (her decision 5) |
| 32 | Organisation settings switch: "On"/"Off" in words, the two hint sentences, the confirm "Switch off birthdays and anniversaries?" with "(412 people)", "Keep it on" / "Switch off", one tap to switch on, "Switched off for everyone.", "Last changed by …" | yes |

**Differences that need her yes:**

1. **Where My profile is opened.** The drawing shows "My profile" as an item in the left menu (and "Me" on the phone's bottom bar). Her decision 2 said "from the account menu". The live portal has an account menu only on the phone, so: on the phone it is in the account menu; on a laptop, the person's name at the bottom of the left menu opens it. No item was added to the left menu or the bottom bar. If she wants the drawn menu item, it is one line.
2. **The prototype's review bar could show "Work anniversaries" only** (birthdays off, anniversaries on). The approved spec (Q2) has one switch for both, so that state does not exist in the product. Nothing built for it.
3. **The prototype's "My profile" has no "Back to Home" link**, and neither does the build (the menu and the bottom bar take you back). Noted only because the Compose screen has one.

## Acceptance criteria for C

| AC | Status | Proof |
|---|---|---|
| 77 approver set at filing, shared | met | `test_filing_sets_the_approver` (the approver can submit), `test_the_department_approver_is_used…`, `test_an_approver_without_the_role_gets_a_share` (Frappe HR's DocShare with submit) |
| 78 | **replaced by decision 4** | `test_a_claim_with_no_approver_is_refused` (the words, and no claim is created) |
| 79 backfill | met | `test_backfill_sets_open_claims_and_a_second_run_changes_nothing` |
| 80, 81 part filters and keys | met | `test_the_approver_sees_the_claim_with_exactly_the_agreed_keys` |
| 82 nobody else; Guest; no Active Employee | met | `test_nobody_else_sees_it` (another approver, an HR Manager, the claimant, a colleague: count 0), `test_a_caller_with_no_active_employee_gets_no_rows` |
| 83 existing inbox tests over the new part, with real portal claims | met | inbox modules below; the Part C tests file real claims with approvers |
| 84 not the approver, HR included | met | `test_only_the_named_approver_decides` (pin) |
| 85 approver who has left | met | `test_an_approver_who_has_left_is_refused` |
| 86 approve submits, GL entry, no shortcuts | met | `test_approve_posts_once…` (2 or more GL rows), `test_decide_expense_has_no_permission_shortcuts` |
| 87 decline reason 1 to 140, stored, no GL | met | `test_decline_needs_a_reason_stores_it_as_text_and_posts_nothing` |
| 88 twice: "already decided", one set of GL | met for one after the other | same test (approve then approve, approve then decline). A true two-connection race was not run; the row lock is the guard (as in Part B) |
| 89, 90 sheet text, escaping, toasts | met | DOM test |
| 91 self-approval on portal, `doc.submit()` and REST | met | `test_nobody_decides_their_own_claim_on_any_door` (pin), with the HR Setting at 0 |
| 92 "Declined: <reason>", escaped | met | DOM test |
| 93 B never sees A's reason | met | `test_the_claimant_reads_their_own_reason_and_nobody_elses` |
| 94 title still from `remark` | met | same decline test |
| 95, 96 fixed keys, no year, no seeded date | met | `test_birthday_reply_has_no_year` (pin) |
| 97 own branch; no branch or no Employee gets nothing | met | `test_own_branch_active_and_not_hidden_only`, `test_no_branch_or_no_employee_sees_nobody` |
| 98 leavers, no date, opted out | met | same, plus `test_a_person_who_leaves_disappears` |
| 99 5 rows, order, See all, empty | met | Python (`test_years_today_first_and_the_card_cap`) and DOM |
| 100 completed years, not this year's joiners, 29 Feb | met | `test_years…`, `test_29_february_shows_on_the_28th_in_a_short_year` |
| 101 switch off: nothing, zero Employee queries, card absent | met | `test_switch_off_returns_nothing_and_reads_nobody` (pin), DOM, browser check |
| 102 one query; 5,000 in one branch timed | **partly**: one query with every filter in SQL; timed at 245 in one branch, not 5,000 | Measurements |
| 103 ships off; only HR Manager / System Manager; Version history; "Last changed by" | met | `test_the_switch_ships_off`, `test_only_hr_manager_changes_the_switch_and_history_says_who` (a plain employee and an HR User are refused) |
| 104 the confirm when switching off | met | DOM |
| 105 own record only; HR's Desk save ignored | met | `test_the_tick_changes_only_my_own_record`, `test_hr_cannot_change_someone_elses_tick` (doc save and `frappe.client.set_value`) |
| 106 tick words; hidden when off | met | DOM |
| 119 | Part B | |
| 120 colleague cannot read the dates through Frappe | met **with the Employee User Permission real data has** | `test_a_colleague_cannot_read_the_dates_through_frappe` (see bad news 4) |
| 121 own claims only; guessed id refused | met | `test_only_the_named_approver_decides`, `test_expense_claims_are_not_visible_across_employees` |

## Tests run, and what they said

All Python in my own container `hrlocal-076c`, site `test076c`, one module at a time, nothing else running against it. Where `bench run-tests` printed two batch summaries, both are listed.

| Module | Result |
|---|---|
| `test_expense_birthdays_076` (new) | 30 ran, OK (also re-run after the break checks: OK) |
| `test_home_076` | 6 OK, then 18 OK (one test changed on purpose: the part list) |
| `test_expense_and_scoping` | 8 OK (fixtures changed on purpose: claimants get an approver). **Before that change, 4 failed with "Ask HR to set your approver."** - which is decision 4 working |
| `test_inbox_parts_042` | 25 OK |
| `test_inbox_counts_034` | 17 OK, then 2 OK |
| `test_count_matches_list_045` | 2 OK |
| `test_browser_call_args_045` | 6 OK |
| `test_frame_endpoint_registry_034` | 9 OK (one bypass declared on purpose; it failed until I did) |
| `test_portal_security_010` | 45 OK, then 5 OK (the `ignore_permissions` ceilings: Part C adds none) |
| `test_employee_field_rights_alv215` | 20 OK |
| `test_erpnext_integration_178` | 15 OK (claims still post to the ledger with the new hook) |
| `test_access_control` | 34 OK |
| `test_notices_076` | 9 OK |
| `test_announcements_076` | 59 OK |
| Frappe HR's own `test_expense_claim` | **could not run on this site**: test discovery stops on a Fiscal Year clash in its own setup ("Year start date or end date is overlapping with Fiscal Year TEST-2025-2026"), before any test runs. Not caused by Part C; CI builds a fresh site and runs it there. The new `before_submit` hook only refuses a submit by the claim's own employee |

**Each guard broken on purpose, and its tests failed** (then the files were put back, `__pycache__` cleared, and the module passed again): the named-approver check removed (`test_only_the_named_approver_decides` failed); the Expense Claim self-approval hook removed (`test_nobody_decides_their_own_claim_on_any_door`, `test_the_hook_is_registered` failed); the switch's early return removed (`test_switch_off_returns_nothing_and_reads_nobody` failed); the opt-out filter removed from the SQL (`test_own_branch_active_and_not_hidden_only`, `test_the_tick_changes_only_my_own_record` failed). 9 tests failed in all, each where it should.

**DOM (jsdom, `NODE_PATH` borrowed from the 063 worktree):** the new file 56 of 56; the whole suite **19 run, 0 failed** (Part A 77, Part B 75 unchanged).

**Static checks, all OK:** `check_app_integrity.py` (860), `check_scope_traps.py`, `check_tag_balance.py`, `check_design_system.py`, `check_brand_spelling.py`, `check_api_paths.py --max 0`, `check_portal_handlers.js`, `check_undefined_js.js`, `check_day_widget.js`, `check_portal_trays.js --static`.

**Not run:** the whole app suite (due once before the dev push); a real logged-in browser session on my site (the balance check uses the real page with a fake server).

## Measurements (query counts are the proof; times on this machine are a record only)

**The Pending card (`get_inbox`), before and after Part C, birthdays switched on.** Same code before, same sites, 10 warm runs each.

| Persona | 20 people: before → after | 980 people: before → after | Payload change |
|---|---|---|---|
| Employee | 14 → 15 | 17 → 18 | +151 bytes |
| Manager | 23 → 24 | 23 → 24 | +151 bytes |
| Store HR | 28 → 30 | 37 → 39 | +151 bytes |
| Company HR | 28 → 30 | 37 → 39 | +151 bytes |
| System Manager | 27 → 28 | 30 → 31 | +151 bytes |

The new part costs 1 or 2 statements (the count and the list, both `get_list`), the same at both sizes, plus one more read of claim lines only when there are claims on the page. Slowest p95 after: 141.6 ms (System Manager, 980 people), inside the 500 ms budget. The difference between the two sizes for HR callers is Part A's known attendance-fix cost (Part A bad news 1), not Part C's.

**Whole Home after Part C** (every Home call added up): 62 to 78 queries at 20 people, 65 to 87 at 980, payload 4.4 KB to 28 KB, depending on the persona.

**Birthdays:**

| Case | Statements | Time | Payload |
|---|---|---|---|
| Switch off | 1 (the switch); **no Employee query** (tested) | | `{"on": 0}` |
| Switched on, viewer with no branch (the measured fixture personas) | 2 | p95 under 9 ms | 46 bytes |
| Switched on, 245 people in one branch, 82 of them with a date this month (on the 980 site, rolled back after) | 2 counted, one of them the birthdays query, all filters in SQL | card: p50 20.9 ms, p95 24.7 ms; See all: p95 18 ms | card 428 bytes; See all 6.3 KB |

**AC-102 asked for 5,000 people in one branch. I measured 245** (the largest company on my biggest site). The query reads one branch and filters the month in SQL, so the time grows with the people in that one branch: about 20 times this at 5,000, still a single query. Not measured, so not claimed.

To time the 245-person case I copied a throwaway script into **my own** container's `/tmp` with `docker cp`, ran it, rolled back its changes and deleted it. No shared or server container was touched; I mention it because `docker cp` is on the "ask first" list for deploys.

## Real-browser balance check (`scripts/browser_check_home_076.js`, Chrome)

The real page, real CSS and real `portal.js`, with a fake server. 5 personas × 3 data sizes × 3 widths (1280 pinned sidebar, 1280 collapsed, 360) × birthdays off and on = **90 cells: 90 passed, 0 failed.**

- Largest gap 24 px everywhere; columns end together; no list over 5 rows (Pending, Notices, Birthdays); no sideways scroll; phone order check-in, Pending, Notices; the Birthdays card present exactly when switched on.
- Worst tallest-to-median ratio 1.69 (rule is 2.0). No card over 2x the median in any cell.
- Pairs stretched beyond 1.5x on natural height, named, not hidden: Leave balance beside Birthdays with 200 rows (1.76x); Pending beside Notices for a frontline person with few rows (2.13x); Team goals beside My documents for a manager with 200 rows (1.73x).
- Grid 984 px wide at 1280, columns 484 px (as Part A found).
- **Reminder of bad news 3:** these are the first runs where Pending and Notices actually had rows.

## The seven dimensions, against the code I wrote

| Dimension | Before to after | Why |
|---|---|---|
| Performance | degrades slightly | Pending: +1 or +2 statements and +151 bytes, the same at 20 and 980 people. Birthdays: one more call on Home; nothing read while switched off; one query when on. All inside the 500 ms budget. |
| Security | degrades by design, then held | Money can now be approved from a phone. Held by: the named-approver check after a row lock, the Active Employee check, the self-approval hook on every door, Frappe HR's own role and field rules (no `ignore_permissions`), a fixed key list. |
| Reliability | improves | A claim always has someone who can see it, or it is refused with a next step. A second tap gets "already decided". The backfill cannot stop a migrate (a claim that will not save is counted and left). |
| Scalability | neutral | One more inbox part (two queries); one birthdays query per Home load, only when switched on, with all filters in SQL. |
| Maintainability | neutral | One endpoint, one part, one small module, three Custom Fields, four hook lines. No new DocType, no abstraction. |
| Data integrity | improves | Filed claims carry an approver; a decline zeroes the sanctioned amount (Frappe HR) and posts nothing; the reason has its own field, so the claim's title is never overwritten. |
| Compliance / privacy | degrades by design, then held | Day, month and years of service become visible inside a branch. Held by: switch off by default, per-person opt-out honoured in SQL, fixed key list, no year or age. Counsel's written note is still needed (bad news 1). |

## What else moved while I worked

- My branch started at `origin/dev` `cf65c663`. I fetched again before committing: nothing new had come in.
- I did not touch the main checkout, the shared bench or any other session's site. My sites are copies of Part B's test sites, made under new names.

## Known gaps

| Gap | Label |
|---|---|
| DTC expense approvers not counted (bad news 1) | **release blocker**; a read-only count removes it |
| Counsel's written birthday note (bad news 1) | **release blocker** for switching birthdays on; the switch ships off |
| A Department approver without the Expense Approver role cannot decide (bad news 2) | intentional trade-off (no `ignore_permissions`); HR gives the role |
| The race "approve and decline at the same moment" proven by the lock and by tests one after the other, not by two live connections | acceptable simplification |
| A desk-made claim with several lines shows its first line's type, date and note in Pending; the amount is the total | acceptable simplification |
| Frappe HR's anniversary emails ignore the opt-out (Q5) | accepted 28 Oct; the tick says "on Home" |
| The discarded `/hrms-employee-next` page now shows a seventh inbox part with its count | acceptable (as the strategy said) |
| Measurement data on my sites | remove with the sites |
| The 5,000-in-one-branch timing (AC-102) was done at 245 | acceptable simplification; one query, rate given |
| Frappe HR's own Expense Claim tests not run here (fixture clash on this site) | temporary debt; CI's fresh site runs them |

## Subtract pass

Removed on this pass: a "Switched on for everyone." toast (not drawn); a "Back to Home" link on My profile (not drawn); my own first cake icon (replaced by the drawn one). Rejected before writing: a new DocType or settings page for the switch (a Custom Field on HR Settings has history for free); a wrapper around Frappe HR's approver lookup in Desk (one 6-line function with two callers); a second endpoint for My profile (it reads the same birthdays call); a separate "my opt-out" field read (the birthdays call returns `hidden`).

Kept, and why: the "Expense Approver role" check in `decide_expense` (without it a Department approver gets Frappe HR's confusing "Approval Status must be 'Approved' or 'Rejected'"); `keep_hide_birthday` (without it HR could change a person's opt-out in Desk, AC-105); the backfill's per-claim savepoint (without it one bad old claim would stop a tenant's migrate); `birthdays_switch_state` (the confirm needs the head count and the page needs "Last changed by").
