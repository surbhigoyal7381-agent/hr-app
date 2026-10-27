---
slice: 071-unseated-names
artifact: 06-review (senior architect review, change-process step 5; the agent file calls it 05-review)
author: hrms-technofunctional-reviewer
date: 2026-10-25
branch: slice/071-unseated-names, 9 commits on origin/dev f207e82c (origin/dev has not moved since)
status: advice. Surbhi decides whether this ships.
---

# 071 · Names in the "In no seat" tray — review

## Verdict: SHIP WITH FIXES

**The code does what Surbhi approved, and I found no leak, no permission gap and no half-write.
But two gates are still open: the full test suite has never finished, and I could not get one
clean run of the slice's own server tests, because other sessions were running tests on the
same site at the same time.**

`SHIP WITH FIXES` means: ready to present for the push decision once the three fixes below are
done. It is not permission to push.

### Read this first

| # | What | Label |
|---|---|---|
| 1 | **The full suite was never completed** (engineer's notes: stopped after 6.5 hours, no summary). CI on a fresh site, or one full run on a clean container, is still owed. | Proven (notes); P2 gate |
| 2 | **My two runs of `test_unseated_071` on test071 failed (1 fail + 5 errors, then 5 errors).** The cause is other sessions, not the code: the testing log shows runs of the same module starting at 15:45:00 and 15:45:59 UTC, overlapping, plus more at 15:34, 15:57 and 16:07, and `test_positions_064` and `test_portal_security_010` after that. The test base class (`OrgCase._clear`) deletes **every** position and assignment on the site and commits, so two runs at once destroy each other's data. The colliding runs left five "Scope194" employees behind (HR-EMP-02305, -02308, -02312, -02318, -02321). **Until they are removed, 5 of the 8 tests on test071 will error with "User ... is already assigned to Employee".** I did not remove them: another session was still using the site. | Proven (log, console); not a code defect |
| 3 | The engineer reports 8 OK (run alone, earlier). I could not confirm that myself. | Not checked by me |
| 4 | Browser checks (phone layout, print, real Escape) not run by me: no web server was running in hrlocal-071. I read the checks instead. | Not checked |
| 5 | Upstream gaps: no `01c` security/privacy requirements, no `07` DevOps notes, no separate test report. The spec and impact analysis (`04`) were written by the engineer who built the code. I reviewed against `02-design.md`, the approved prototype and Surbhi's decisions as given to me. | Proven (folder listing) |

Also: **my runs and the other sessions' runs wiped the positions on test071** (now 0 positions, 0
assignments). The engineer's browser seed ("Demo071 Retail") needs re-seeding before any more
browser checks there.

## The three fixes before a push

1. Remove the five leftover Scope194 employees on test071 (or use a fresh site), then run
   `test_unseated_071` **alone**, with no other test run on that site. Expect 8 OK.
2. Get the full suite green once: CI on a fresh site, or one uninterrupted full run.
3. Surbhi says yes or no to the four parity differences (list below).

None of these is a code change.

---

## Blockers

None found.

## Majors

None found in the code. Fix 1 and fix 2 above are the P2 items.

## Minors (P3: can ship if written down with an owner)

**m1 · Two HR people placing into the last free place at the same moment can over-fill the seat.
P3, existed before this slice.**
- *State:* seat "Cashier · Sector 34" has 2 places, 1 person. HR A and HR B each press "Place in
  seat" for different people within the same second.
- *What happens:* both requests pass `_check_position_not_overfilled`
  (`alvoraa_position_assignment.py`, runs in `on_update`). It counts with a plain read
  (`frappe.get_all`), which in MariaDB's default isolation does not see the other request's
  row until it commits. Both commit. The seat shows 3 of 2.
- *Why it matters:* the chart's counts are wrong until somebody notices.
- *Label:* Inferred from the code, not run.
- *"Place anyway" is safe:* the extra place goes through `save_position` → `doc.save()`, and
  Frappe's `check_if_latest` locks the seat row (`get_doc(..., for_update=True)`, Frappe 16.33.1
  `document.py:1432`). The second request either waits and adds its own place correctly, or
  stops with Frappe's "has been modified after you have opened it" message and saves nothing.
  Inferred, not run.
- *Smallest fix (only if Surbhi wants it):* lock the seat row at the top of `assign_person`
  (`frappe.get_doc(POSITION, position, for_update=True)` in `_position_in_scope`). One line. It
  is outside what was approved, so it is her call, not a condition of this slice.
- *Debt label:* temporary debt, removed by that one line.

**m2 · "Place in seat" on a seat with only half a place free fails on the first try. P3.**
- *State:* seat has 2 places, 1.5 filled. `posUnRoom` (`portal.js`, "room = half a place open")
  shows "Place in seat". The dialog opens with share 100.
- *What happens:* `assign_person` → the over-fill rule refuses: "… has 2 seat(s) and would be
  filled 2.5 times over." HR must lower the share to 50 and press again.
- *Why it matters:* it is the agreed rule (design §3, "Room = today's rule"), but the message
  does not say what to do, and "2.5 times over" is wrong arithmetic (it is the head count, not a
  multiple). The wording bug existed before.
- *Smallest fix:* when opening from the tray, set the share to the free part of the seat
  (`min(100, open × 100)`). About one line. Needs Surbhi's yes because it changes the dialog.
- *Label:* Proven by reading `posUnRoom` and `_check_position_not_overfilled`; not run. Rare at
  DTC, where seats hold whole people.

## Nits and P4 (backlog)

- **n1** The server test proves "another *branch's* seat is refused with add_place", but not
  "another *company's* seat". Same lines guard both (`register.py:617-620`), so the risk is low.
  Add one test.
- **n2** `add_place` on a seat that is already over-filled (old data) adds one place, which may
  still be too few, and then `_check_seats` says "It cannot be **reduced** to N seats" while the
  user was adding. Edge case; nothing is saved.
- **n3** The dialog searches `employee_name` only, with a limit of 20. A one-word name that is
  part of 20 or more other names could push the person off the list. Then the pick is cleared
  (PD14) and Save asks to choose: nothing wrong is saved. Accepted as R-4 in the strategy.

## Noticed, outside this slice (separate tickets, not part of the verdict)

- **`assign_person` never checks that the *employee* is inside the editor's companies or
  branches** — only the seat (`register.py:749`, `_position_in_scope`). Through the API, HR of
  company A can place company B's employee ID in A's seat; that person's name then shows on A's
  chart. The 071 tray only offers people already in the reader's scope, so the new screen does not
  open this path, and `add_place` does not widen it. Owner: `hrms-security-privacy-engineer`.
  Proven by reading; not exploited.
- **070's own check "070 AC-63: Try again loads again" fails once 070 is rebased on today's
  `dev`**, with or without 071: the 066 grooming bell timer (`gmBellLoad`) makes a third fetch
  during the check. Proven: I ran 070's checks on 070 merged with `origin/dev` alone and got the
  same failure. That is 070's to fix when it rebases. Owner: whoever lands 070.
- `portal_correction_test.js` is flaky on `origin/dev` (engineer's note). It passed in my run.

---

## Trying to break it

| Attack | Result | Label |
|---|---|---|
| Non-HR reader opens Positions | Server sends no `unseated` key → no tile, no tray. Unchanged by 071; covered by `test_positions_064.test_a_reader_without_hr_scope_gets_no_list_at_all` | Proven (code + test read) |
| HR of another company / another branch | `_unseated` filters by `permitted_employee_filters()` inside the database; tests `test_another_companys_person_is_never_listed`, `test_store_hr_gets_only_their_branch_and_nobody_with_no_branch` | Proven (code + test read) |
| Exactly which fields go out | Six named keys (`UNSEATED_KEYS`), pinned by `test_each_person_carries_exactly_the_six_allowed_fields`. 071 sends nothing new. | Proven |
| `add_place` by a user without Write on Position | Refused before anything happens (`_position_in_scope` → `may_edit`). Test `test_somebody_who_may_not_change_seats_is_refused` | Proven (code); test not run cleanly by me |
| `add_place` on another branch's seat | Refused, count unchanged. Test exists | Proven (code) |
| `add_place` on another company's seat | Refused by the same check | Proven (code); no test (n1) |
| `add_place` by a non-HR owner who has Write on Position | Allowed. That is not new power: they can already set any seat count with `save_position` | Inferred |
| Seat count trusted from the browser? | No. Read fresh on the server; the browser only sends a yes/no flag | Proven (`register.py:782-785`) |
| Atomicity: place added, then placement refused | Everything rolls back: no `commit` between `save_position` and the insert; no `doc_events` on Alvoraa Position. Test `test_a_refusal_after_the_place_is_added_leaves_the_count_as_it_was` uses a savepoint, so an inner commit would also break it | Proven (code); test not run cleanly by me |
| Two HR, last place, at once | See m1 | Inferred |
| Full-seat flow | "This seat is full" + "Place anyway" → confirm with focus on Cancel → "Add a place and continue" → dialog says 7 → 8 → server adds exactly one | Proven by node checks I ran (219 OK) |
| Escape | Confirm, then dialog, then tray; a dialog that already handled the key (`pos-delete`) leaves the tray. Read the handler and the 7 node checks | Proven (node) |
| Duplicate names | Pre-pick by employee ID; ID shown in every candidate line and every tray row; a pick not in the new list is cleared | Proven (node, two "Ravi Kumar") |
| Phone layout | CSS floors scoped to `#pos-person`, `#pos-full`, `.pos-un*`; browser checks exist | Not checked by me (no server) |
| Print (Ctrl+P, wall chart) | `.pos-sheet`, `#pos-layer` and every `.gp-backdrop` are `display:none` in print; the new confirm is a `.gp-backdrop`. Wall chart node check (183) passes | Proven by CSS read + node; browser print not run by me |
| XSS through a name | Every name goes through `posEsc`; the context line uses `textContent`; onclick IDs go through `posJs` | Proven (read) |

## Hot files: 072 (seats follow reporting, was 070), 070 (readable on phone), 065, 066

Trial merges (`git merge-tree`, nothing written to any branch):

| Branch | With 071 | Note |
|---|---|---|
| `slice/070-seats-follow-reporting` (slice 072, renumbered) | portal.js, positions.html, panels.css, register.py merge cleanly. **One conflict:** `scripts/check_positions_tree.js`, both appended a section 22. Keep both; chain `deleteChecks().then(unChecks).then(seats070)`. With that, all 071 checks pass on the merged code | Proven (ran it) |
| `slice/070-readable-on-phone` | Clean | Re-check US-6 "no answer" texts if it changes how `gpFetch` fails (071 tests `e.name === "TypeError"`) |
| `slice/063-field-rights` | Clean | — |
| `slice/066-retention` | Clean | — |
| `slice/065-option-a`, `065-plan-a-replacement`, `066-attendance-decide` | Conflicts | **All already conflict with `origin/dev` without 071**; none is caused by 071 |

Incoming work: `origin/dev` = `f207e82c`, which the branch is already on. The 20 slice-066
grooming commits that came in during the build are named in the engineer's notes. Nothing new has
landed since.

---

## AC verification

From `04` §2 (US-1 to US-12) and `02` §9.

| AC | Result | Evidence |
|---|---|---|
| US-1 rows: name link (new tab), grey ID, joined (+year), No manager chip, sorted, once each | Met | `posUnseatedSheet`; node "071 rows" (8), ran |
| US-2 300 people, one paint, no call | Partial | One string, one `innerHTML`, no fetch (read). Never rendered at 300 in a browser (engineer's note) |
| US-3 room → Place in seat → dialog for that seat, picked by ID, context line, share 100, approvals off | Met | node "071 dialog" checks, ran |
| US-4 full → words + Place anyway → confirm, focus Cancel, 7 → 8 | Met | node "071 full/confirm", ran |
| US-5 saving: "Putting them in…", stays open until reload, note, counts and tile drop by one | Met | node "071 save/success" (6), ran |
| US-6 errors: no answer / refusal / lost but saved | Met | node (4), ran. Depends on `gpFetch` error shape |
| US-7 empty sentence | Met | node, ran |
| US-8 HR User without Write: names, no buttons; server refuses | Met | node + server test (read) |
| US-9 no matching seat: no button | Met | node, ran |
| US-10 not HR: no tile | Met | unchanged; `test_positions_064` (read) |
| US-11 print: no unseated name or ID | Met (CSS + node); browser not run by me | panels.css print block; `browser_check_positions.js` print checks (read) |
| US-12 keyboard: Escape top layer only, focus back, Tab order | Met (node); real browser not run by me | 7 node Escape checks, ran |
| D1: one `add_place` flag, all-or-nothing | Met | `register.py:782-785`; rollback test (read; see fix 1) |
| Q3: two matching seats → the one with room | Met | node "071 Q3", ran |

## NFR verification

| Budget | Measured or reasoned | Result |
|---|---|---|
| Opening the tray | No server call; payload unchanged | Pass (read) |
| Statements per placement | Engineer measured 10 plain, 26 with add place (`test_statement_count_is_a_fixed_handful`, which only asserts ≤ 40) | Pass on the engineer's number; I could not re-measure |
| 82 to 300 names | One string build; browser at 82 by engineer; 300 not rendered | Not measured at 300 |
| Phone floors (44 px, 12 px, 16 px) | Browser checks exist | Not checked by me |

Seven dimensions, the impact analysis (`04` §6, notes) against the code:

| Dimension | Claimed | My finding |
|---|---|---|
| Performance | neutral | Agree. Fixed handful of statements per click |
| Security | neutral | Agree for 071. No new endpoint, no new `ignore_permissions`. Pre-existing employee-scope gap noted separately |
| Reliability | improves | Agree. Escape, stale pick, all-or-nothing all proven in node / code |
| Scalability | neutral; "two HR at once … refused whole" | **Partly wrong.** True for "Place anyway" (row lock). Not true for plain "Place in seat" into the last place (m1). Existed before 071 |
| Maintainability | neutral | Agree. ~155 JS lines; `posPickSeat` keeps the editor path untouched |
| Data integrity | improves | Agree for add-place. Same m1 caveat |
| Compliance / privacy | neutral | Agree. Same six fields to the same readers; nothing on paper; nothing logged |

## Compliance verification

There is no compliance sub-analysis in a spec (no `01c`, no `02-functional-spec`). The brief's
privacy section and Surbhi's decisions name four obligations; I checked those. Anything beyond
them is **unreviewable** on this axis.

| Obligation | Mechanism | Test | Result |
|---|---|---|---|
| Names only to System Manager, HR Manager, HR User, inside their own companies/branches | `permitted_employee_filters()` in `_unseated` (from slice 064, unchanged) | `test_positions_064` (5 scope tests, read) | Discharged (by 064; 071 adds no data) |
| Panels never print | `@media print` hides `.pos-sheet`, `#pos-layer`, `.gp-backdrop` | `browser_check_positions.js` print with tray, dialog, confirm open (read, not run by me) | Discharged on code; browser proof not re-run |
| A raised seat count is traceable | Alvoraa Position `track_changes: 1` → Version row with seats before and after, same user as the assignment | Engineer saw it on test071 | Discharged (read json) |
| Hand rollback | `04` §8.4 steps; no new code | — | Discharged as a written procedure |

---

## Prototype parity

Built as drawn. I compared the strings and markup of `prototype-v1.html` with the build: row
layout, button words, confirm text, context line, success note, empty sentence, error texts all
match.

The four differences the engineer listed, still waiting for Surbhi's yes:

1. "N in all" uses `seats + 1`, the prototype `ceil(seats) + 1` (differs only for 7.5-place seats).
2. Dialog title stays a `div` (prototype: `h2`).
3. Dialog field labels stay `div`s (prototype: `<label for>`).
4. `.pos-sheet h2:focus{outline:none}` also affects the seat tray and the "No reporting manager"
   tray headings.

**Other differences I found:** none visible. One wording detail: the success note drops " · branch"
when the seat has no branch; the prototype always adds it. Invisible at DTC, where every matching
seat has a branch (a seat only matches by branch).

## What to delete

Nothing. Each new piece has a caller or a job Surbhi approved: `posPickSeat` keeps the editor path
untouched; `posUnRoom` has three callers; the "lost but saved" re-read makes the error text true
(approved US-6). I looked hard at the re-read (about 10 lines for a rare case); it is the
cheapest way to keep "not in the seat" from being a false statement, so it stays.

No new DocType, field, endpoint, setting, flag, cache or dependency. Rung: new code in an existing
panel, plus one optional argument on an existing endpoint. Cheaper rungs were rightly rejected
(Frappe's Employee list cannot filter "holds no seat").

## What was done well

- **The extra place is added on the server, inside the same request (D1).** It turns a
  three-call browser dance that could leave a seat at 8 with nobody new into one transaction, and
  the count is read fresh, never taken from the browser.
- **A seat with 0 places is treated as "no limit" (E1)**, caught before build. Without it, "Place
  anyway" would have quietly turned "no limit" into "1".
- **Pick by employee ID, and clear a pick that left the list (PD14).** That closes the
  duplicate-name mix-up at the cause, not just on screen.
- **The rollback test uses a savepoint**, so it would also fail if anybody later added a commit
  between the two writes.
- **Every guard was broken once on purpose** to prove its check fails.

## Confidence

| Claim | Basis |
|---|---|
| No names reach a reader outside HR scope | Proven: code + existing tests read; 071 sends nothing new |
| All-or-nothing add place | Proven by code read; test exists; **not run cleanly by me** |
| JS behaviour (rows, buttons, confirm, dialog, Escape, errors) | Proven: I ran `check_positions_tree.js` (219 checks, 0 failures), `check_wall_chart.js` (183), `run_dom_tests.js` (13 run, 0 failed) with `NODE_PATH` = `064-old-v2/node_modules` |
| `scripts/check_app_integrity.py` | Ran: 822 checks, OK (doctype-shadowing check skipped, no bench path) |
| `test_unseated_071` | **Not proven by me.** Two runs failed from overlapping runs by other sessions (see Read this first) |
| Phone layout, real print, real focus | Not checked: no web server in hrlocal-071. Needs a running site and Playwright |
| Full suite | Not run by anyone to the end |
| Race behaviour | Inferred from Frappe 16.33.1 source and MariaDB isolation; not run |

### Questions

- **Must know (holds the push, not the verdict):** fixes 1 to 3 above.
- **Should know:** does Surbhi want m1 (one-line row lock) and m2 (share set to the free part)
  in this slice, or as tickets? I rank both P3 meanwhile.

## Subtract pass on this review

Removed: a finding about the "lost" detection depending on `gpFetch`'s error shape (it is
already a written risk with a rebase step); a finding about `aria-pressed` on candidate lines
(prototype parity, approved); a note about desk access for HR User (an assumption already
recorded as A1). Kept everything else because each changes what Surbhi does next.
