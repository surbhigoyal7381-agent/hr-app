---
slice: 088d (a person's change to a day record is on the change notice)
author: hrms-fullstack-engineer
date: 2026-11-26
worktree: /Users/mac/hr-app/.claude/worktrees/088d-attendance-scope, branch docs/088d-attendance-scope (review fixes added 27 Nov, see the last section)
built on: origin/dev 8a62945d (ALV-469 came in while I worked; see "What else moved")
status: built and tested on my own stack (d088-*). NOT pushed. `register_notice.py` edited in the review round only (four lines, below), after the page-count fix landed.
---

# 088d implementation notes

## Read this first (what changed my mind, and what needs Surbhi)
1. **Q1 was reversed on 26 Nov (Surbhi): only a change to a day that already had a record is listed.** A day with no earlier record being marked for the first time is not asked about and not listed, so "Mark Attendance" and the Employee Attendance Tool work again with the switch on. What the reversal touched is in "Q1 reversal" below. (She first chose "listed", then reversed it when this note showed that listing first marks refused both tools for every use.)
2. **Security finding, proven over real HTTP (not a notice problem; it predates this slice; raised as ALV-477, not fixed here):** an HR login with API access can change the engine's own pay fields on a *submitted* day record. `PUT /api/resource/Attendance/<name>` with `{"alvoraa_slab_quarters": 5, "alvoraa_reds": 9}` returned **200 and the values changed**, with the notice switch OFF and no reason. Those fields are `read_only` in the form but `allow_on_submit`, and Frappe does not enforce `read_only` on the server. With the switch ON the same call is refused without a reason, and with one it succeeds and is listed as "Day record changed" (generic, it does not say the engine's fields). Who can do it: HR User, HR Manager, System Manager (they hold write on Attendance). A Version row is written (`track_changes`), so it is not silent, but nothing says "an engine field". Not fixed here (out of scope); it needs its own decision: a `validate_update_after_submit`-style guard that refuses a person's write to the 11 engine fields.
3. **00d said Data Import "skips Frappe's Select check". True at document level, but Data Import also checks a Select column against its options before it starts.** A bad reason code stopped the import at the template stage (status stays Pending, a warning names the invalid value). So F3 for the code is half closed by Frappe itself; our check is the backstop for rows that get past it, and the only check for the text rules (below).

## What was built (rung per item)
| File | What | Rung |
|---|---|---|
| `alvoraa_portal/day_change.py` (new, about 290 lines) | `at_a_door`, the Attendance handlers (`before_validate`, `on_submit`, `before_update_after_submit`, `on_update_after_submit`, `before_cancel`, `on_cancel`), the two tool wrappers, `after_migrate` | new code |
| `punch_change.py` | `reason_problem` (code and text together; replaces `_valid_reason`), `add_row` (the one writer of the log), `why_line` (what the paper prints), `clean_text`, text support in `require_reason` and `write_log`, text Custom Field on the punch | existing |
| `alvoraa_punch_change.json` | `attendance` and `reason_text` fields; `punch` no longer required; the last option is now "Other"; `modified` bumped so migrate syncs it | existing DocType (name kept) |
| `hooks.py` | Attendance `doc_events` +6 entries; two `override_whitelisted_methods`; `day_change.after_migrate` in both lists | hot file; re-read after fetch, ALV-469 touched 4 lines elsewhere, no clash |
| `tests/test_day_change_088d.py` (new) | 55 tests | |
| Custom Fields (via `after_migrate`) | `alvoraa_change_reason` and `alvoraa_change_reason_text` on Attendance (`allow_on_submit`); `alvoraa_change_reason_text` on Employee Checkin | customisation |

**Not changed:** `register_notice.py` (see the four lines below), anything in `hrms`/`erpnext`/`frappe`, any JS.

## The four lines waiting for `register_notice.py` (apply after the page-count fix lands)
All four are in `register_notice.py` on `origin/dev` 8a62945d; the line numbers will move.
1. `_punch_changes`, the `fields=[...]` list (line 262): add `"reason_text"`.
2. `_punch_changes`, `row.update(...)` (line 280): add `reason_text=r.reason_text`.
3. `_content_hash`, the punch branch tuple (line 536): add `"reason_text"` after `"reason_code"`.
4. `sheet_rows`, the punch branch (line 558): `"why": punch_change.why_line(change.get("reason_code"), change.get("reason_text"))` instead of `change.get("reason_code")`.
Until then a day-change row prints, and "Other" prints as just "Other". Everything else already reads the log. `punch_change.why_line` exists and is the only thing the fourth line calls.

## How the door test works (what I built, and what I proved of it)
`at_a_door()` is true when the request or job was addressed to Attendance: the Desk `savedocs`, `cancel` and `discard`, `frappe.client.*`, the list bulk action (and its queued job), the Data Import (by its reference doctype, as a command or a queued job), the upload tool (command and job), and the REST path (`/api/resource/Attendance`, `/api/v2/document/Attendance`). It reads memory only, so a system write costs nothing.
- **Proven over real HTTP** on my stack with a real API login: `frappe.client.submit` (refused without a reason, accepted with one), REST `PUT` on a submitted row (refused without, accepted with), `frappe.client.cancel` (refused with the two-step sentence), and a real queued Data Import (below). So the REST path door and the `cmd` doors work in a real request, not only in a test that sets `form_dict`.
- **A test trap found on the way:** `frappe.set_user` wipes `frappe.form_dict`. My first run set the door and then the user, so no door was ever seen and every "refused" test failed while every system test passed for the wrong reason. Fixed (user first, then door). Worth knowing for anyone writing a door test.

## The 31 paths (`TheSystemAndTheOtherRecordsPass`, `ThePathTableDoors`; run 55 of 55 OK)
Each id appears in a test name; `test_every_path_has_a_test` fails if one is dropped. **How each was driven, honestly:**
- **Driven as the real function with the switch ON, in a person's session with a door of another record, and shown not refused and not listed:** A01, A02, A03, A05, A06 (two tests), A07, A08, A09, A10 (one notice entry, no log row), A12, A13, A14 (with `confirmed=1`), A27, A28, A31.
- **Driven as a person at a door, listed or refused as designed:** A16 (a replacement is listed; a first mark is not), A17 (two), A18, A19 (two), A20, A21, A22, A23 (a first mark works, a replacement is refused loudly; the stock swallow; switch off), A24 (same, plus the half-day tick; switch off).
- **Door detection only (not the full operation):** A25 (upload: command and job recognised), A26 (Data Import: recognised by reference doctype). The full import was driven separately over HTTP (below).
- **Hook-less writes, documented not guarded:** A04, A15, A29/A30 (a `set_value`, raw SQL and a `qb.update` leave no trace; the tests assert exactly that, so a future change is noticed).
- **Not driven:** A11 (087 undo; needs a disputed request; the test only names the known gap).

## What was done about the silent "marked successfully" (after the Q1 reversal)
**Chosen: refuse up front, loudly, but only where a row would be replaced.** `mark_bulk_attendance` and `mark_employee_attendance` stay wrapped (`override_whitelisted_methods`). They now check **before any row is touched**: does a day in the request already have a cancelled record for that person? If so, and the switch is on and the user is a person, they get one clear sentence and nothing is changed. The Employee Attendance Tool's half-day tick (`qb.update`, no hook, changes existing rows) is refused the same way. A first mark passes straight to the stock function. **The wrappers are not dead code, checked:** with the replacement check disabled (break W1) `test_A23` fails with `ValidationError not raised` (the stock loop swallows the row, as `test_A23b` shows), and the tool test fails with the per-row sentence in place of the tool's. The upload tool and Data Import report each failed row, so they needed no wrapper. With the switch off both tools call the stock function unchanged.

## Q1 reversal: what it touched
- `day_change.py`: `before_validate` now demands a reason and stashes a log row **only when `_was(doc)` finds an earlier record** (an amended row, or a cancelled row for the same person and day); otherwise it blanks the reason fields and returns. `_submit_sentence` lost its "Day marked ..." branch (now only "Day changed from X to Y" or "Day record replaced, still X"). The two tool wrappers changed from "refuse always" to "refuse a replacement or the tick" (above). The module docstring says which acts are listed.
- `tests/test_day_change_088d.py`: a helper `cancelled_day()` (a day that had a record, now cancelled) replaces `a_day()` wherever a test expected a listed change; new `test_A16a` (a first mark, with or without a reason, is neither asked about nor listed; a reason typed on a first mark is dropped, not logged); `test_A23` and `test_A24` rewritten (first mark works, replacement refused, tick refused); one more test, 55 in all.
- **Nothing else changed:** `punch_change.py`, `hooks.py`, the DocType JSON and the four held `register_notice.py` lines are as before. The sentence the notice-read-back test expects changed to "Day changed from Absent to Present".
- **Cost on the person's side:** a first mark by a person now costs one extra read (the earlier-record lookup), the same one a replacement already paid. System writes still cost 0 queries (re-measured: 0 at 20 rows, 0 at 1,000; whole insert 21.00 a row at 20 and at 100).
- Breaks for this round: Q1 (listing first marks again) makes `test_A16a` fail (`AssertionError: None is not true`: the first mark was refused) and `test_A23` fail with the raised "Pick a reason" error; W1 above; W2 (tick check removed) failed on a stock error (`IntegrityError: Column 'late_entry' cannot be null`, the stock tick crashing on the test's arguments), **not** on "not raised", so it shows the tick would reach the stock code but not by a clean assertion.

## Three warnings worth keeping
1. **`frappe.set_user` wipes `frappe.form_dict`.** (`frappe/__init__.py` `set_user` sets `local.form_dict = _dict()`.) Set the user first, then the door. My first run did it the other way round: no door was ever seen, so every system test passed for the wrong reason and every refusal test failed. A door test that passes for the wrong reason is worse than one that fails.
2. **Break B5 (100-character cap removed) did not fail the way it should.** Frappe's own column limit caught it first (`CharacterLengthExceededError`), so the test failed on a message mismatch, not on "not raised". The cap is doubly guarded; the break proves only the outer (Frappe) guard, not ours. I did not count it as proof of our cap.
3. **`test_portal_security_010` shows 13 errors on my stack. All are `No module named 'frappe.core.doctype.kpi'`.** The KPI doctype belongs to `alvoraa_goals`, which my site does not install. Environmental, not a regression. I opened one and grouped the other twelve by name; the ceiling rows for `punch_change.py` and `register_notice.py` are in the passing part. (Not re-run this round: nothing in it changed.)

## The Data Import, run for real
A real queued import of 5 rows through a worker, as an HR login with the System Manager and HR User roles (a plain HR Manager is refused creating a Data Import at all, and an HR Manager without HR User may not import Attendance):
| Row | File said | Result in the Data Import log |
|---|---|---|
| 1 | valid reason | imported, submitted, logged "Day marked Present" |
| 2 | no reason | refused: "Pick a reason for this change. It is printed on the employee's monthly notice. (If you are importing ... put it in the 'Reason For This Change' column ... on every row.)" |
| 3 | reason that is not "Other", with text | refused: "This row has text in 'Reason Text' but the reason is not 'Other'. Clear the text, or set the reason to 'Other'." |
| 4 | "Other" with text | imported, logged with the text |
| 5 | "Other", no text | refused: "The reason is 'Other', so say what happened in 'Reason Text' (up to 100 characters)." |
The log shows the **row number** beside each sentence (`row_indexes`), and the import ends "Partial Success". A first import with a reason code that is not on the list never started: Frappe's own pre-check kept it Pending with "The following values are invalid: ... Values must be one of ...". Not done: an import of **punches** with the same file shapes was driven only as a unit test (`test_F3...`, with `in_import` set, after a control proving Frappe then accepts a bad Select value); I did not run a real queued punch import.

## Query counts (the two figures asked for)
- **Our handlers on a system write (no door): 0 queries at 20 rows and 0 at 1,000.** Measured by calling all five handlers that many times on a document with a name (so a stray write would be counted). With the `on_cancel` guard removed (break B8) it reads 20 and 1,000.
- **A whole `mark_attendance` insert (the auto path's own function): 21.00 queries a row at 20 rows and 21.00 at 100.** I did **not** run 1,000 whole inserts: at about 3 seconds each it is about 50 minutes a run. The per-row figure is flat from 20 to 100, and our part of it is the 0 above. **Not measured:** wall time with the handlers removed (A/B). **Not measured** against a real month-end.

## Every break, and what the test said
Done on committed code, restored after each (the file was copied back). "Wrong value" = an assertion on a value; "setup error" = a crash before the assertion.
| Break | Test | What it said |
|---|---|---|
| B1 door always true | A02, A06, A08 | all three: `ValidationError: Pick a reason for this change...` raised **inside the leave approval, the request approval and the Shift Type click**. This is the failure the whole design exists to avoid, and the tests catch it. (Raised error, not a wrong value, but it is the real refusal.) |
| B2 door always false | control, A16 | `AssertionError: ValidationError not raised`; `ValueError: not enough values to unpack (expected 1, got 0)` (no log row) |
| B3 demand removed | control | `AssertionError: ValidationError not raised` |
| B4 text with a non-"Other" code allowed | text test, F3 test | `AssertionError: ValidationError not raised` (both) |
| B5 100-character cap removed | cap test | **Not the failure I wanted.** Frappe's own column limit then stopped it (`CharacterLengthExceededError`), so the test failed on a message mismatch, not "not raised". The cap is doubly guarded; the test proves the sentence, not that our cap is the only guard. |
| B6 every save counted as a change | A17b | wrong value: a log row existed where none should |
| B7 tool refusal removed | A23, A24 | `ValidationError not raised`; message mismatch (the per-row reason sentence instead of the tool sentence) |
| B8 `on_cancel` always writes | cost test | wrong value: `(20, 1000) != (0, 0)` (after I made the fixture carry a name; the first version of that test **passed under the break** and could not fail, which is how I found it) |
| B9 "was" forgotten | A19 | wrong value: `'Day marked Absent' != 'Day changed from Present to Absent'` |
| B10 import skips our check | F3 | `AssertionError: ValidationError not raised` |

## Suites run (own stack, `test_site`, one at a time, `throttle_user_limit` set to 1000 as an integer: a string value crashes every user creation)
| Suite | Result |
|---|---|
| `test_day_change_088d` (new) | **55 of 55 OK** (final run, after the Q1 reversal) |
| `test_invoicing` | OK (4) |
| `test_attendance_doors_085` | 16 OK |
| `test_punch_change_088c` | 40 OK |
| `test_register_notice_088` | 80 OK |
| `test_payroll_reprocess` | 12 OK |
| `test_alv291_attendance_fix` | 5 OK |
| `test_attendance_request_shift_346` | 5 OK |
| `test_company_scope_085` | 20 OK |
| `test_held_team_086` | 33 OK |
| `test_held_day_085` | 39 OK, **6 fail** (same six as 03c: the backfill script path is not mounted; environmental) |
| `test_leave_063_card_cancel` | 17 OK |
| `test_punch_fix_087` | 134 OK |
| `test_portal_security_010` | 45 + 5 + 20: **13 errors, all `No module named 'frappe.core.doctype.kpi'`**: the KPI doctype belongs to `alvoraa_goals`, which my site does not install. Environmental, shown for one test (`test_sec9_approve_kpi_update_refuses_own`); the other twelve are the same group by name (goals and evidence), **not opened one by one**. The ceiling rows for `punch_change.py` and `register_notice.py` are in the passing part. |

Also: `scripts/check_app_integrity.py` OK (1071 checks); `scripts/check_brand_spelling.py` first FAILED (my refusal log text said "Alvoraa Punch Change", a name a person could read) and was fixed to "punch_change.add_row"; now OK.

## NFRs, against the code
- **Performance:** neutral. Zero queries on a system write; a person at a door pays one read for the earlier row.
- **Security:** improves. Server-side; the code-and-text check also runs under import; refusals are written down (`088d-*` rules). One pre-existing hole found (finding 2 at the top).
- **Reliability:** the risk is a wrong door answer. The path table pins every system path as not refused. A refusal inside a stock bulk loop is made loud by refusing up front.
- **Scalability:** neutral.
- **Maintainability:** one door constant. `punch_change.add_row` is now the single writer of the log.
- **Data integrity:** the log row and the Attendance save are in one transaction. The reason is cleared after logging.
- **Privacy:** free text is capped, one line, shown escaped (Frappe also strips event attributes from Data fields on save; observed with `<img src=x onerror=1>`). A hint on the field says no medical details or other people's names. Not in any log line.

## What else moved while I worked
`origin/dev` moved from e82bb3f0 to 8a62945d: six ALV-469 commits (another engineer: `org_label.py`, `email_brand.py`, `hooks.py` +4 lines, two patches, frame templates, tests). I read the file list; none touches Attendance or the punch log. I rebased my two commits on top without conflict. Nothing of theirs was changed.

## Known gaps and shortcuts
- **Dangerous debt (escalate):** the REST write to engine fields (top, finding 2).
- **Temporary debt:** 1,000-row whole-insert figure not run; punch import not run for real; A11 not driven; A25 only door detection; the four `register_notice.py` lines wait on the page-count fix; no A/B wall time.
- **Acceptable simplification:** the log keeps its name; `_changed` compares cast values per field type rather than a list of fields.
- **Existing, not mine, seen on the way:** `punch_change._moved` compares `doc.get_value(...)` on `shift_start`/`shift_end`, and Frappe's `get_value` turns an empty Datetime into "now", so two empty values compare unequal. I hit it in my own comparison and avoided it there. Whether it makes a punch with no shift tag look "changed" in 088c was **not checked**.


---

# Review fixes (05d, "Ship with fixes"): what was done, item by item

Dev was `e705daff` when this round started and moved twice more (ALV-480 and a toast commit; nothing near Attendance, the punch log or `hooks.py`). Everything below was run on a fresh stack, `throttle_user_limit` set to the integer 1000 first.

| # | Finding | What I did | Proof |
|---|---|---|---|
| P1-1 | `run_doc_method` is a door | `day_change.py`: `run_doc_method` and `runserverobj` added to `_FORM_CMDS`; `dt` added to the doctype read; for API v2 (no `cmd`) the path `/api/v2/method/run_doc_method` is a door when `document` names an Attendance. The doctype is still compared exactly, so the Shift Type click (same command, a Shift Type in `docs`) stays outside. | Written first and run against the code with the fix removed: cancel, submit and v2 tests failed (`ValidationError not raised` x2, `False is not true`); the Shift Type regression passed. Then **over real HTTP**: `POST /api/method/run_doc_method` cancel with no reason was refused with the two-step sentence (417) and the row stayed submitted; with the reason saved first it cancelled, and the reason was cleared. `POST /api/v2/method/run_doc_method` with no reason: 417, row still submitted. |
| 1 / P2-3 | wrappers act before permission | `frappe.has_permission("Attendance", "write", throw=True)` first in both | test: an employee login gets `PermissionError` for a day with and for a day without a cancelled record (same answer). |
| 2 / P2-2 | empty shift tag reads as a change (088c code) | `punch_change.same(df, a, b)` (cast by type, empty equals empty) now serves `_moved` and the shift branch of `_sentence`; `day_change` uses the same function (no third comparison). I also replaced `get_value` on `skip_auto_attendance` with a plain read. | test: an untagged punch saved with nothing changed is not demanded and not logged; changing only its time does not say "shift". |
| 3 / P2-1 | "names what moved" | **Built as approved.** `_was` now reads `status`, `leave_type`, `half_day_status`, `shift`. Status changed: "Day changed from A to B". Status same, others moved: "Day changed: half day" (labels "leave type", "half day", "shift"). Nothing moved: "Day record replaced, still X". I did not decide it was dropped; it simply was not built in round 1 and I did not say so. | three tests (half-day flip; leave type and shift; nothing moved). |
| 4 / P3-5 | wrong `cmd` string | A02, A03, A04 now use `run_doc_method` with a Shift Type in `docs`. **And one more test, found while breaking P1-1:** `A02b`. With first marks no longer demanded (the Q1 reversal), the three original tests could not tell a too-wide door from a right one, because a first mark is never refused. `A02b` re-marks a day that has a cancelled record (the real case: HR resets a day, then the click or the job puts it back). | break R1 below. |
| 5 / P3-6 | path-table test only spelled names | `test_A11` now drives the 087 undo and pins the gap (the undo happens, no log row). The path-table test now also fails if a path's test has no assertion. **It still checks names and the presence of an assertion. It does not prove coverage of behaviour.** | break R10. |
| 6 / P3-4 | W2 half-day tick not proven needed | `test_A24c`: the stock tool called directly, switch ON, as a person: `half_day_status` changed and `rows()` is empty. That is the hole shown, not described. | passes. |
| 7 / P3-7 | outside the ceiling gate | `("alvoraa_portal", "day_change.py"): 1` in `CEILINGS`; `test_portal_security_010` run (this time with `alvoraa_goals` installed, see results). | |
| 8 / P3-8 | decision 5 had no test | `TheTwoLines`: a 087 fix then a person's day cancel gives two rows on the notice list, one the request and one the log row. | break R8b: a merge makes it `1 != 2`. |
| 9 / P3-9 | repeated reads in the person test | **Measured, not changed.** 500 calls cost 1.00 query a call (not two: one of the two is cached by Frappe). Next to the stock 21 queries a row that is under 5 percent, at human pace, and only for a person at a door. No cache built. `test_a_person_at_a_door_costs_two_reads_a_row_and_no_more` keeps the number (it fails above 2.0). | printed: `088d person test: 1.00 queries a row (500 rows)` |
| 10 / P3-10 | reason left on a cancelled row | `on_cancel` clears the two fields whenever they hold anything, by whoever cancelled; no query when they are empty (so system cancels still cost 0). | break R7. |
| 11 / P3-11 | `reason_text` in the hash | see "register_notice.py" below. |

## Breaks this round and exactly what they said
| Break | Test | Failure |
|---|---|---|
| R2 P1-1 fix removed (test-first) | cancel, submit, v2 | `AssertionError: ValidationError not raised` (cancel and submit), `AssertionError: False is not true` (v2). Wrong values, right reason. |
| R1 door too wide: any `run_doc_method` is a door | `test_the_shift_type_click_is_still_not_a_door` | `AssertionError: True is not false` (wrong value). **The three original system tests (A02, A03, leave cancel) passed under this break**, which is why A02b was added. |
| R1b the same break, against A02b | A02b | `ValidationError: Pick a reason for this change...` raised **inside the Shift Type click**: the real refusal of HR's daily button. |
| R3 permission check removed | wrappers test | `AssertionError: PermissionError not raised` |
| R4 `_moved` back to `get_value` | untagged no-op | `AssertionError: True is not false : nothing moved` |
| R5 shift branch back to `get_value` | time-only change | `AssertionError: 'shift' unexpectedly found in 'punch moved from 06:10 to 06:20; punch shift changed'`: the false sentence itself |
| R6 `_was` status only | half-day, leave type and shift | `'Day record replaced, still Half Day' != 'Day changed: half day'` and `... != 'Day changed: leave type, shift'` |
| R7 clearing removed | reason left behind | `Tuples differ: ('Other', 'typed words') != (None, None)` |
| R8 "merge" first attempt | two lines | **Did not fail.** My break suppressed a log row when another log row existed, and the fix leaves no log row, so it changed nothing. Not counted. |
| R8b merge done properly (suppress the log row when an approved request exists that day) | two lines | `AssertionError: 1 != 2 : cause and consequence, never merged` |
| R9 v2 door removed | v2 | `AssertionError: False is not true` |
| R10 A11's assertions removed | path-table test | `Lists differ: ['test_A11_...'] != []`: the hollow test is named |

## register_notice.py (item 11): the four lines, applied
CI on dev was green on `7769f73c`, which includes the page-count fix (`e705daff`'s own CI was cancelled by the next push; `7e126677` and later passed). I re-read the file first: the line numbers had moved from `8a62945d`.
1. `_punch_changes` `fields=[...]`: `"reason_text"` added.
2. `_punch_changes` `row.update(...)`: `reason_text=r.reason_text` added.
3. `_content_hash` punch tuple: `"reason_text"` added. **Effect:** a log row's fingerprint now has one more part, so a fingerprint taken before this change would not match. No notice has ever been printed on any tenant (the switch is off everywhere), so there is nothing to mismatch. Stated so nobody is surprised later.
4. `sheet_rows` punch branch: `"why": punch_change.why_line(code, text)` (so "Other" prints "Other: <words>"). `my_changes` (the employee's own view) uses the same function, so both screens follow.
Test: `test_the_typed_words_are_printed_and_are_part_of_the_fingerprint`. Break: hash without `reason_text` fails `AssertionError: '3fc3...' == '3fc3...'` (the fingerprint did not move); why line without the text fails `AssertionError: 'Other' != 'Other: reader cable cut'`.

## Results this round (own stack; `alvoraa_goals` installed this time, so no KPI errors)
| Suite | Result |
|---|---|
| `test_day_change_088d` | 72 tests: 71 OK on the full run, plus the new fingerprint test run alone (OK) |
| `test_portal_security_010` | **45 + 5 OK** (the 13 KPI errors of last round were the missing app; with `alvoraa_goals` installed they pass), ceiling row for `day_change.py` included |
| `test_punch_change_088c` | 40 OK (after the `_moved` and sentence change) |
| `test_register_notice_088` | 82 OK, with the four lines in. **Two caveats, both mine, both environmental, shown:** (a) on a run after my real-HTTP probes one test failed because probe rows I had committed sat in a month the test expects empty; (b) on a second run of the whole suite on the same database two photo tests failed with "That photo was already used", because the first run's photo `File` rows are committed and stay. In both cases I removed my leftovers and the tests passed. The photo one means the 088 suite cannot be run twice on one database without cleaning; that is 088's own, not changed by me. |
| `test_punch_fix_087` | 134 OK (after I reset the notice switch I had left on; with it on every fixture punch filed as Administrator is correctly refused: it looked like 50 failures and was my own leftover) |
| `test_alv302_sync_punch` 62, `test_checkin_security_014` 14+2, `test_field_checkin_fixes_013` 16, `test_punch_dedupe_alv337` 26, `test_attendance_doors_085` 16, `test_invoicing` 4+20 | all OK |
| `check_app_integrity.py` | OK (1078 checks) |
| `check_brand_spelling.py` | OK |

## Still unproven / said plainly
- The path-table test checks names and that each test asserts; it does not prove each path's behaviour is covered.
- A Workflow on Attendance is not a door (05d section 3). One line for the switch-on runbook: do not put a Workflow on Attendance.
- Finding P4: a reason typed on a first mark is dropped without telling the person.
- The two bulk job branches (`_bulk_action`, `start_import`) are proven by a real queued import (last round) and source reading, not by a unit test.
- The 1,000-row whole insert (about 50 minutes) and an A/B wall time were not run.
- ALV-477 is not touched.
