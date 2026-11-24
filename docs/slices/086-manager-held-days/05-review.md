---
slice: 086-manager-held-days
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-11-23
read: worktree /Users/mac/hr-app/.claude/worktrees/086-manager-held-days, branch slice/086-manager-held-days, HEAD eb8f781f, base origin/dev 412d5361 (diff 412d5361..HEAD, 15 commits, 18 files)
ran on: stack alv086-bench / alv086-db (site test_site, apps bind-mounted from this worktree - checked with docker inspect)
status: review only. Nothing edited outside this file, nothing pushed, nothing deployed.
---

# 086 - Senior architect review (step 5)

## 1. Verdict: SHIP WITH FIXES

**No P0 and no P1. One P2 must be fixed or accepted in writing before release:** the duplicate check in
`send_held` is a locking read on a table with no index on `employee`, so every row of every send locks the
whole Attendance Request table. That is the real cause of the deadlocks the test stage saw, and of
managers who lose a race getting all 50 rows "not sent". The rest is small. SHIP WITH FIXES means ready to
present for a decision once fixed - it is never permission to push or deploy.

What I could and could not check, up front:
- **Proven by running:** `test_held_team_086_proof` on alv086-bench: 11 tests, OK (81.7 s). That module has
  11 tests in total, so the one summary covers all of them. I did not re-run the other modules; their
  numbers in `04-test-report.md` are **the test engineer's, not mine**.
- **Proven by reading the database:** the last deadlock InnoDB recorded on alv086-db (`SHOW ENGINE INNODB
  STATUS`), the indexes of `tabAttendance Request` and `tabAttendance`, and the query plan.
- **Not checked:** any browser walk (screens judged by reading `portal.js` against `prototype-v2.html`),
  DTC's real Attendance Request row count, nginx, a real phone.
- **Incoming work:** my local `origin/dev` ref is 3 commits past the base (0a181d05); one of them changes
  `punch_fix.py` (+40 lines). I did not fetch, and I did not read those commits. The rebase must read them.
- **Someone else's file in this worktree:** `alvoraa_portal/tests/test_zz_secreview_086_probe.py`
  (untracked). Inferred to be the parallel security review's (06). Not mine, not read, not run.

## 2. Blockers

None.

## 3. Majors

### M-1 (P2) The duplicate check locks the whole Attendance Request table on every row - this is the deadlock

`held_team.py:246` - `frappe.db.get_value(REQUEST, _open_filters(...), "name", for_update=True)`.

- **Proven (database):** Frappe adds `ORDER BY creation DESC LIMIT 1 FOR UPDATE`. `tabAttendance Request`
  has only three indexes: `PRIMARY`, `creation`, `alvoraa_branch_index` - none on `employee` or
  `from_date`. `EXPLAIN` picks `type=index, key=creation`: a scan of the whole index.
- **Proven (deadlock record, 07:57:20 today):** transaction 1 held **794 row locks** on the `creation`
  index, plus the "supremum" (end of table) lock, and was waiting to INSERT. Transaction 2 was this exact
  query (`... employee='HR-EMP-01025' AND from_date='2026-11-14' ... FOR UPDATE`) waiting for the same
  index. InnoDB rolled transaction 2 back.
- **Scenario:** two managers press Send within a second of each other, for different people. Each row's
  locking scan locks every request row and the end of the table. Each row's INSERT then needs the end of
  the table. The two sends block each other, and one gets a deadlock. Its first row usually fails, the
  loop stops (`held_team.py:195`), and that manager sees 50 rows "Not sent. The office was busy". On
  DTC's Monday morning, with many managers, this is a normal day, not a rare race.
- **Why it is wrong:** the strategy and the notes claim "locks taken in sorted order so two overlapping
  sends do not deadlock" (03, Scalability row). Sorted order cannot help when each row locks the whole
  table. The scan also grows with the table (every row of a 50-row send reads every request on the
  site), and while it holds those locks, any other Attendance Request insert on the site (an employee's
  own 087 request, HR) waits.
- **Data stays safe** (the answer matches the database, earlier rows stay filed). That is why this is P2,
  not P1.
- **Smallest fix (engineer chooses, both must be proven by TheLock and a repeat of the three-manager HTTP
  run with 0 deadlocks):**
  - (a) Drop `for_update` from the duplicate read. The day-row lock (`held_team.py:242`, Attendance has an
    `employee` index) already makes a second send for the same person and day wait. To make the plain
    read see the first send's committed request, end the transaction at the top of each row (one
    `frappe.db.commit()` before `savepoint`), so the read after the day lock starts a fresh snapshot.
    TheLock (which starts an old snapshot on purpose) is the test that proves it.
  - (b) Keep the locking read and give it an index on `employee` (Property Setter `search_index` on the
    hrms field). Narrower locks, but a schema change on an hrms table and a migrate.
  - I recommend (a): no schema change, and it deletes a lock instead of adding an index.

## 4. Minors

### m-1 (P3) Held view with no held days left - stale Show box, no chip, missing prototype words

`portal.js:17632-17649` (`hdlRender`). The Show box replaces the filters only when `d.days` is non-empty.
- **Scenario A (inferred from code, not browser-checked):** a manager sends the last held days. `hdlDone`
  calls `hdlLoad`, which calls `hdlRender` with no days. The bar is not redrawn, so it still shows the old
  Show box, e.g. "20 Nov 2026 (5)", for days that are now empty. The Held chip disappears (`total` is 0),
  so no chip is selected.
- **Scenario B (the notes' case):** the page opens on the Held view with no held days (`trLoad` ->
  `trBar`), so the full From/To/Person/Group-by block shows.
- **Against prototype-v2 (`listHtml`, empty state):** v2 shows the paragraph "No held day without a
  request is waiting for you. When somebody forgets to punch, the day shows up here." (not drawn), and a
  primary button "Show {day}" (built shows only the date).
- **Answer to question 4:** yes, it is a parity gap, but a small one. It does not block. Smallest fix:
  when there are no days, put the banner, the v2 empty block and "See everything" on the page and switch
  the page back to Everything (`trState.only = ""` plus `trBar()`), or ask Surbhi to accept it as is.

### m-2 (P3) Remaining parity differences against prototype-v2 (her rule: each needs her yes or a fix)

Read from code, not seen in a browser:
| v2 draws | Built | Where |
|---|---|---|
| "Change" (with an aria-label) next to the question | "Change to leaving" / "Change to arrival" as visible text | `portal.js:17700` |
| 3+ punches: "Where is the missing punch?" and "Show the punches and tap the gap" | "What time was the missing punch?" and "Choose where the missing punch goes" | `portal.js:17684`, `hdlGapBlock` |
| "Punches: ... · Shift 09:00-18:00" | "Punches on this day: ..." (the shift is only in the strip) | `hdlRow` |
| Triangle icon on each row's Held label | Label only (the chip has the icon) | `hdlRow` |
| Day headings in "All days" mode | None (each row shows its date) | `hdlRender` |
| "All days in this period (1 to 20 Nov)" | No date range | `portal.js:17631` |
None changes what is sent. One list for Surbhi: accept or fix.

### m-3 (P4) The deadlock test does not prove AC-32's "rows before stay filed"

`test_held_team_086_proof.py:79-102` checks only that no row is called "sent" without a request. It would
also pass if the code rolled everything back and answered "not sent" for both rows. Add one assert: the
first row is `ok` and its request exists.

## 5. Answers to the six questions

1. **Commit per row: safe, keep it.** Proven by reading: `ok` is set only after `frappe.db.commit()`
   returns (`held_team.py:184-185`), so the answer cannot say "sent" for a row that is not committed. The
   commit is only in `held_team.py`; `raise_for_report` and its other callers are unchanged, so no other
   caller commits. Frappe's `commit()` runs the after-commit callbacks per row instead of once per
   request - harmless here. The trade-off (a send is no longer all-or-nothing) was never visible to the
   manager (AC-28). Cost found: tests that call `send_held` now leave data behind, and `_wipe` must clean
   it (the test stage already fixed that; its known limit is named in 04).
   **`_undo_row` is correct.** After a deadlock, InnoDB has already rolled back the whole transaction, so
   the savepoint is gone (1305). The plain `rollback()` then only resets Frappe's state, and since every
   earlier row is committed, nothing but this row is lost. `log_refusal` writes to a file, not the
   database (`hrms/.../access.py:71-93`), so the plain rollback loses no refusal log. A lock-wait timeout
   keeps the savepoint, so the first branch is used.
2. **Day-row lock: keep it.** It now has its own test (`TheDayLock`, in the 11 I ran: OK), and the test
   engineer broke it and watched it fail. It is also the lock that fix M-1 (a) relies on. The "known gap"
   in 03 is closed.
3. **All 50 "not sent" for the loser: a fix, not acceptable as designed.** It is a side effect of M-1,
   not of commit-per-row. Fix M-1 and the race mostly disappears (two managers rarely share a person).
4. **Empty Held view:** yes, a parity gap, P3 (m-1).
5. **Parity:** the main journey matches v2 (chip with icon, Show box, line and explanation, strip and real
   punches, no pre-fill, required reason with the D-4 line, Ready, fixed bar, confirm, banner, "Go to the
   first one", refusal words). Differences are in m-1 and m-2. Subtract pass in section 8.
6. **NFRs:** section 6.

## 6. NFR check - the seven dimensions against the code

| Dimension | 03 claim | My finding | Label |
|---|---|---|---|
| Performance | neutral, list is 4 queries | List: agree (6 queries measured by the test stage, flat). **Send: each row scans the whole request table with locks** (M-1); grows with table size | proven (EXPLAIN, deadlock record); size effect inferred |
| Security | improves | Agree. D-1 guard now for every caller (`attendance_correction.py:2488-2499`), per-row scope with one fixed sentence (`held_team.py:174-178`), D-2 edit and delete guard, POST only, 30 an hour, no `ignore_permissions` | proven by reading; tests per 04 |
| Reliability | improves | Agree for one manager (no 500, answer is true). Concurrent sends deadlock (M-1) | proven |
| Scalability | neutral, "sorted order, no deadlock" | **Degrades. The claim is disproved** by the deadlock record (M-1) | proven |
| Maintainability | neutral | Agree. One new file, rules stay in `raise_for_report`. Small duplication: `_refuse_edit_by_others` reads the employee's login twice | proven by reading |
| Data integrity | improves | Agree. "One of n" line after a blank line (D-3); answer matches the database (04's 12-send comparison - **not re-run by me**) | inferred from code + 04 |
| Compliance / privacy | improves | Agree. Error Log holds manager id and counts only (`held_team.py:207-210`); rows carry five keys; reason never logged (marker test in the 11 I ran) | proven |

## 7. AC and compliance checks

I walked these against the code myself. The other ACs rest on 04's mapping, which I read but did not
re-verify one by one.

| AC / item | Result | Evidence |
|---|---|---|
| AC-1, 2, 8 list scope | met | `_team()` direct reports only; open request hides the day; proof tests ran OK |
| AC-5 empty state | partial | m-1 |
| AC-19 cap of 50 | met | `held_team.py` refuses over 50, whole send; proof test ran OK |
| AC-22..24, SEC-1 per-row scope | met | `held_team.py:174-178`, fixed sentence, no name; colleague/stranger/guest test ran OK |
| AC-25, 26 future time, In/Out | met | `_file_one`; break tests in 03 |
| AC-31, SEC-5 one request per day | met | day lock + locking duplicate read; TheLock and TheDayLock. M-1 changes how, not whether |
| AC-32, OPS-56 stop, keep what went | met (thinly tested) | commit per row; m-3 |
| AC-35 limit words | met | `_limited(..., message=)`; default unchanged for other callers |
| AC-44 over 50 ready | moot | unreachable: a page holds at most 50 rows (section 8) |
| SEC-7 filer guard (D-2) | discharged | `punch_fix._refuse_edit_by_others`, `refuse_delete_by_others`, `hooks.py` on_trash; TheFilerGuard |
| SEC-8 stamp names the manager id | discharged | `attendance_correction.py` stamp; proof test ran OK |
| PRIV-2 no reason in logs | discharged | marker test ran OK |
| PRIV-3 row shape | discharged | `_shaped` returns name, day, shift, punch time and source only |
| D-4 reason printed on the notice | discharged as decided | warning line on each reason box; the only protection, by her choice |

## 8. What to delete

- **The locking duplicate read** (M-1, fix a): remove `for_update=True` at `held_team.py:246`.
- **The "over 50 ready" line** in `hdlBar` (`portal.js:17846`): it can never show. Ready rows come only
  from the current page, and a page holds at most 50. Delete it (and mark AC-44 as moot).
- Nothing else. I looked for an unused helper, flag, setting, cache or new field and found none.

## 9. What was done well

- Every request still goes through `raise_for_report`. No rule is copied, so 087's reason rule, window
  and switch apply unchanged.
- Committing each row and setting `ok` only after the commit makes the answer true even after a real
  deadlock. That is the right fix for the test stage's P1, and its fallback was proven by breaking it.
- The test stage's two-connection lock tests use real database connections, and two hollow tests were
  caught and rewritten. That is the standard to keep.
- `_limited` got an optional message with the old sentence as default: no other caller's words change.

## 10. Subtract pass on this review

Removed from my draft: a finding on the generic `except Exception` branch (a lost database connection
could still give a 500) - real but rare and not specific to this slice; and a finding on HR approvals
waiting behind a send - covered by M-1's fix.

---

## Re-review after fix round 2 (24 Nov 2026)

**Verdict: SHIP.** Every finding from the first review landed and matches prototype-v2. I found no new defect. SHIP means ready to present for push approval. It is not permission to push.

**Where I looked.** Worktree `/Users/mac/hr-app/.claude/worktrees/086-manager-held-days`, branch `slice/086-manager-held-days`, HEAD `36d701b5`, base `origin/dev` `0a181d05`. I read `62bd524e` and `d7937ad8` in full, the "Fix round 2" section of 03, and the parts of `held_team.py` and `punch_fix.py` the fix depends on. Stack `alv086-bench`, site `test_site`. I proved it mounts this worktree with `docker inspect`.

**Tests I ran myself:**
| What | Result | Label |
|---|---|---|
| `test_held_team_086` | **33 OK** (427 s) | proven |
| `test_held_team_086_proof` | **11 OK** | proven |
| `portal_held_team_086_test.js` (DOM test) | **27 passed, 0 failed** | proven |
| The other modules in 03's table, the 3 managers x 50 rows HTTP run, and the break tests | not re-run by me. The figures are the engineer's | not checked |

**Warning about the test stack.** My first run of `test_held_team_086` gave **19 errors**. While it ran, another session (pid 52024, not mine) was running the same module on the same `test_site`. I stopped my copy and waited for theirs to finish. My solo re-run gave 33 OK. A third run (the proof module) started at the same time, so even that run was not fully alone. Inferred: the 19 errors came from the two runs clashing, not from the code. Whoever owns pid 52024 should not trust a red result from that window.

**M-1 (P2), the deadlock: fixed. Proven by reading, and the test passes.**
- The duplicate check is now a plain read (`held_team.py:262`). `frappe.db.commit()` runs before each row (`:193`). The day-row lock is still there (`:258`).
- **Can two sends get past the check together? No.** I traced this in the code. Sender B blocks on the day-row lock until A commits. A holds that lock until the commit after `_file_one` (`:197`). Under MariaDB's default isolation (repeatable read), a transaction's snapshot is taken at its first plain read. A locking read does not take one. Between B's commit and the lock there is no database read, only `getdate` and `nowdate`. So B's duplicate read takes a fresh snapshot after A's commit and sees A's request. `TheLock` proves the hard case, where B starts its snapshot early on purpose. It passed in my run.
- Inferred, very small: if Frappe had to load the Attendance doctype definition from the database just before the lock (a cold cache), that read would take the snapshot early. I did not prove this can happen. Not a finding.
- Out of scope and not new: an employee filing their own 087 request at the same moment as the manager does not take the day-row lock. Round 1 did not stop that case either.

**Other findings:**
- **m-1 (empty Held view): fixed, matches v2 `listHtml`.** The Show box is redrawn from every answer. The empty block has v2's two sentences, a primary "Show {day}" button and "See everything". The DOM test covers it. Proven.
- **m-2 (six wording differences): all six now match v2.** I checked them against v2's string table: "Change" with the full words as its `aria-label`, "Where is the missing punch?", "Show the punches and tap the gap", "Punches: {0} · Shift", a triangle on each row's label, a day heading in "All days" (the same `.dgrp` style), and the period dates. Proven by reading. Not checked by anyone: the day headings with more than one day, and the Hindi words. v2 has Hindi strings; the build relies on Frappe's `__`.
- **m-3 (P4, deadlock test): fixed.** The test now also checks that the earlier row is still filed (`_proof.py:103-107`). Proven by reading.
- **Subtract: done.** The "over 50 ready" line and `Math.min` are gone. AC-44 is moot.
- **Security F1 and F2: fixed, pinned by two new tests** (they passed in my run of the 33). Known gap, as 03 says: nobody has broken the bad-`day` check to watch its test fail.

**ALV-436 intent: kept. Proven by reading.**
- `_refusal_of` now removes only real tags (`</?letter...>`), so the "< and >" in ALV-436's sentence survives. It still removes `<b>`.
- `test_reason_rules` now expects `<img onerror>` and `<urgent>` to be refused, and `9 > 8` to be filed. That matches ALV-436's own list of reasons that must pass.
- Nit (P4): the docstring at `test_held_team_086.py:271` still says "markup filed as text", and the variable `filed` holds a refusal. The words are wrong, the test is right.

**Seven dimensions, now:**
| Dimension | Verdict | Label |
|---|---|---|
| Performance | improves: no lock on the whole table | proven by reading. Timings are the engineer's |
| Scalability | improves: one row locks one person-day | proven by reading |
| Reliability | improves | concurrency figures not checked by me |
| Security | neutral to round 1 | proven by reading |
| Maintainability | neutral | proven by reading |
| Data integrity | improves: F1 keeps the whole reason | proven by test |
| Compliance / privacy | neutral: no new log content | proven by reading |

**Still open (not blocking):**
- The DOM runner failure in `portal_leave_063_test.js`. The engineer says it fails on `origin/dev` too. Not checked by me.
- The P4 docstring nit above.

**Subtract pass on this section:** I removed a note on the `_limited` change, which did not change this round.
