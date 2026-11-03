# ALV-291 fourth review: commit fa606431

**Verdict: BLOCK.** The new rules did not cancel a person's row in any case I could
build, apart from one gap (a declined request, F2). But step 8 can refuse for good, after
the rows are already cancelled and with the hourly job off, and the runbook has no way out
(B1). The fix is a few lines. The rank is provisional: if the number in B1 is 0 at
DTC, B1 drops away and the verdict becomes **SHIP WITH FIXES**, with six P2s still needing
a fix or Surbhi's written yes.

**What I could not do, said first:**

- **I ran no tests and touched no site.** This was read-only, as asked. Only `ruff` and a
  Python compile ran (both clean). Every finding comes from reading the script, its test
  and Frappe HR's code in this worktree.
- **I had no live DTC data.** Each finding says which count settles it.
- **There is still no impact analysis, spec or test report for this slice.** So I cannot
  check this against claims made before the build, and the compliance axis stays
  unreviewable against a spec. I checked it against the commit message and the runbook.
- I cannot confirm the test suite passes on this commit. I only have the engineer's word.
- Branch: one commit on `ee78a211`, the main release. `origin/dev` has two commits this
  branch lacks (`dcf74d58` ALV-292, `b7841327` ALV-286, same author). By file name neither
  touches this script. I did not read them. Nobody else's commit came in.

---

## 1. Blocker (P1)

### B1. Step 8 refuses for good when a kept day has a loose punch on the wrong shift

**Where:** `alv291_attendance_fix.py:872-875`, against `_plan` lines 463-464.

Step 8 and retag use two different lists:

- `retag` works from `_plan`, which leaves out kept days (line 464).
- `enable_and_mark` works from `_wrong_punches` directly, which keeps them (line 873).

**The case I traced:**

1. Person P's punches on 14 Oct carry old shift X, which is switched off. So the job never
   used them and never flagged them. They are unlinked, with the skip flag at 0.
2. That day has a row the script keeps: a half-day leave, an Attendance Request, or a row
   HR typed. None of these link punches.
3. Preview counts them under "Not retagged, day kept". That line mixes them with harmless
   linked punches, so nothing stands out.
4. cancel_wrong cancels everyone else's rows. Retag skips P's punches, correctly.
5. Step 8 line 873 finds P's punches: wrong shift, no attendance. It refuses with "Run
   cancel_wrong and retag first".
6. Running those again changes nothing. **It refuses every time.**

**Why it is wrong:** this happens after the destructive steps. The rows are cancelled, the
days are empty, and the hourly job is off for all of DTC. The runbook's "If step 8 refuses"
section does not cover it. The only ways out are a code change on a live site, cancelling a
row the script promised to keep, or `undo`, which does not bring the rows back.

- **Proven** by reading. Not run. The fixtures cannot show it: the kept people in the test
  (AMEND, HANDABS, REQ, CONF) have punches on their own default shift, and HAND, FIXADM and
  ABH's leave day have linked punches.
- **Number that settles it:** wrong-tag, unlinked punches on kept days, for the frozen list.
  Preview does not print this today. A leave day on one of the shifts that were off is
  enough, so I expect it not to be 0 `[ASSUMPTION]`.
- **Not from this commit**, and the earlier reviews missed it. This commit makes it more
  likely, because the longer list brings in more kept rows.

**Smallest fix:**

- Line 873: take the list from `_plan(...)["retag"]`, the same one retag uses.
- Line 901: add the kept days to `blocked`, so pass 1 leaves those punches alone. Otherwise
  Frappe flags them, or writes a second row if the two shifts' hours do not overlap.
- Line 1003: verify's `wrong_tag_unlinked` must leave out kept days too, or the runbook's
  "must be 0" fails on these punches.
- Add a fixture: a typed row on a day with an unlinked wrong-tag punch.

---

## 2. P2 findings (each needs a fix or Surbhi's written yes)

### F1. Preview does not show the days or what they will become, so nobody can check them before the cancel

**Where:** preview lines 551-556 and 573-581.

Preview prints per-person counts: "cancel Absent 3, Half Day 1". There are no dates and no
hint of the result. This matters because the rebuild can go three ways:

| Day | Rebuild gives | Why |
|---|---|---|
| In and out punches | Present or Half Day | The intended fix |
| One punch, shift has an Absent threshold | **Absent again**, 0 hours | `calculate_working_hours` reads first to last punch |
| One punch, shift has no threshold | **Present, full day** | `get_attendance` lines 291-300 return Present |

- **A true Absent can turn Present.** Someone on leave drops in and badges once. The job's
  Absent has Frappe's comment, nobody edited it, and the punch is free. So the row is
  cancelled. On a shift with no Absent threshold the day becomes Present.
- **Inferred:** DTC has thresholds on at least some shifts, because the 16 and 22 Oct notes
  describe one-punch days becoming Absent. **Not checked:** which of the 12 shifts.
- **HR may have looked at a day and left it.** That leaves no trace on the row, so no code
  rule can see it. The only control is a person reading the days against the client's
  sheet. The runbook makes that check in step 9, after the rows are gone.
- "Rows to cancel and rebuild from the punches" also suggests the day gets fixed. On a
  one-punch day it does not. Of the 192 days, I cannot say how many have one punch.

**Smallest fix:** one line per row in the badged section: date, current status, number of
usable punches. Add a warning on any shift with no Absent threshold. Then Surbhi can compare
with the sheet at step 5.

### F2. A request HR declined does not protect the day

**Where:** `_plan` line 435 checks only `a.attendance_request`.

1. An employee raises "Marked Absent by Mistake" for 14 Oct.
2. HR declines it with a note. `decide()` (`attendance_correction.py`, the decline path)
   writes only to the request and leaves it as a draft. The Attendance row does not change.
3. The row still looks like the job's own: Administrator, Frappe's comment, not edited.
4. If that day has a free punch, the script cancels it and rebuilds. Two punches make it
   Present.

HR's decision is overturned without anyone being told, and pay follows. **Proven** by reading.

**Number that settles it:** Attendance Requests with review status Declined whose dates
cover a row on the CANCEL list.
**Smallest fix:** one query in `_plan`; keep those days, with the reason "HR declined a request".

### F3. A day "left for a person" can still be cancelled, when its punch was flagged

**Where:** `_wrong_punches` line 303 ignores flagged punches. `_plan` lines 427 and 449.

1. On 14 Oct, an auto Absent. A Frappe-flagged punch sits on old shift X, outside the
   window of the person's right shift.
2. At preview the flagged punch is invisible to `_wrong_punches`, so the day is not
   `blocked`. The row is cancelled and the flag cleared.
3. At retag the punch is no longer flagged. `_wrong_punches` now finds no shift for it and
   the day becomes `blocked`.
4. Step 8 leaves the day out of both passes. **The day has no row at all.**

On a shift that was on, the hourly job later writes an Absent that preview's `PLUS` line
never counted. The hourly job may also mark the punch on old shift X, if X is on. On a shift
that was off, the day stays empty for good. `days_punched_no_attendance` still reads 0,
because it leaves out blocked days. The only sign is that `left_for_a_person` is higher than
preview said.

**Proven** by reading. It breaks the promise made in the third review.
**Smallest fix:** in `_plan`, also work out `blocked_days` for the Frappe-flagged free
punches that are on a shift other than the default.

### F4. A same-minute copy leaves the real punch flagged, and the day rebuilds wrong

**Where:** lines 470-478. The test even records it: `test:344-347`.

The rule "never clear a punch that has a second punch in its minute" comes from the 16 Oct
trap. That was about clearing the *import's* copy while the sync's copy was live. Here it is
the other way round:

- 09:55, flagged by Frappe. 19:05, flagged by Frappe. 19:05:40, the import's copy.
- The row is cancelled. Only 09:55 is cleared. The 19:05 stays flagged, because the minute
  has two records, even though the import's copy will never be used.
- The rebuild sees only 09:55, so 0 hours. At DTC that means **Absent again**, now holding
  a punch. Verify then lists it with the kinds the runbook calls "both correct".

**The test passes for the wrong reason:** line 519 asserts `Present` only because no test
shift has a threshold.

**Size:** the 16 Oct note puts 677 such copies in the 1-6 Oct import, and the 255 Absent
rows you named are 20-31 Oct. So it may be small. Preview does not print it.
**Smallest fix:** count only punches that will be live (leave out import-flagged ones), and
clear one of any Frappe-flagged pair. Print how many stay flagged.

### F5. Verify cannot see a day that was cancelled and then not rebuilt

**Where:** verify lines 957-963 and 976.

Verify only counts unflagged punches for `days_punched_no_attendance`. If a rebuild is
refused, Frappe flags the punches again (`handle_attendance_exception`), so the day counts
as nothing. Example: an Inactive employee. Pass 1 is refused and flagged. Pass 2 skips them
(`get_assigned_employees`). The row is gone, and verify still reads 0.

Other days that end up empty:

- a day now on a holiday list (lines 183-184 skip it), which is visible in verify only if
  the punch is unflagged;
- F3's days.

**Inferred**, since any `ValidationError` in the rebuild takes this path. Most likely few
days. But this is the check that says the run worked, and it cannot show this failure.
**Smallest fix:** in verify, read `state["cancelled"]` and print every cancelled row whose
day has no live row now. About four lines.

### F6. "Too few hours, Frappe is right" may be false, and the runbook calls these days correct

**Where:** line 448; runbook line 150-153.

An Absent holding a punch is kept with that reason. Two known causes do not fit it:

- **A late punch.** The job built the row from the in-punch, and the out-punch arrived later
  and was flagged. That is the same fault as the Half Day rule, which cancels. For Absent,
  the rule keeps the row. Same cause, opposite result.
- **The ALV-211 days.** The code comment at `attendance_correction.py:62-65` counts 535 DTC
  days where a late out-punch fell outside the old 1-hour window, and the day was marked
  Absent. Those punches are marked off-shift, and `_free_punches` skips off-shift punches. The
  22 Oct note says such days stay wrong until re-marked. **Not checked:** whether they were.

The first group is listed as `kept with a punch`. The second is not listed in the badged
section at all, only in verify. Keeping them is safe, but the words tell the operator it is
correct. See the question at the end.

**Smallest fix:** change the reason to "a punch is linked to it: check the hours". In the
runbook, remove "both correct". The rule itself is Surbhi's decision.

---

## 3. P3 (ship, tracked)

- **m1. The no-punch number is wrong when no one is in the badged section** (the engineer's
  soft spot). Line 568 passes an empty list to `_attendance`, which treats empty as "no
  filter". `punched` is then empty too, so **every Absent in the company** is counted as "no
  punch". Display only, but it reads as a guarantee. It also covers only people in the badged
  section, not the whole list. An Absent whose only punch is import-flagged or off-shift
  appears in no bucket. Fix: `badged_people or [""]`, and say who it covers.
- **m2. PEOPLE grows more than the commit says.** `_free_punches` now also returns Frappe-flagged
  punches, so line 391 adds people with a flagged punch on a day with **no row at all**. Their
  flags get cleared. This may be right, but "76 or more" does not explain it, and the badged
  section does not show them.
- **m3. "Undo flags them again" is only partly true.** A punch linked to rebuilt attendance
  stays unflagged, and the `NOT restored` line counts only punch tags (line 1071). After step
  8 almost all of them will be linked. Print the count.
- **m4. Preview after step 8 is a dead end.** The runbook says preview may run "only with the
  same list". But after step 8 the people with nothing left drop out, so preview refuses. The
  numbers can only come from step 8's own refusal, which is the blind copy the runbook forbids.
  Fix: line 504 should compare only people *added*.
- **m5. Punches are matched to rows by calendar day, not by the shift's date.** On a shift whose
  window crosses midnight, a 00:30 punch counts for the next day, and that day's true Absent gets
  cancelled and re-marked. The status does not change. **Not checked:** whether any of DTC's 12
  shifts cross midnight. The longest one I saw named ends 20:30, so 23:30 with the window.
- **m6. Retag's "a little higher" gives the operator nothing to compare.** Preview can print the
  expected extra.
- **Carried from 07:** no log of who changed what. The state file is deleted at step 10. After
  that, nothing shows that this script cleared a flag (`update_modified=False`). Surbhi should
  confirm this is fine for a grievance.

## 4. P4 (backlog)

- A ticked "Auto Update Last Sync" stays ticked after step 8. Line 930 does not restore it, yet
  the message says "put back as they were".
- Half Day proof: a console `set_value` of status with `update_modified=False` on a job-made row
  would look automatic. I found no such write in the repo (grep). Scripts run by hand are not
  checked.
- The refusal at line 887 accepts a last sync of 1 Nov 00:05 on a shift whose window ends after
  midnight, and that would miss 31 Oct. It needs a box left unticked and a very narrow time.

---

## 5. Your eight questions

**1. Can it cancel a row a person made, or a true Absent?**
A row a person typed or edited: no, except with the declined request (F2). A true Absent: yes
on the one-punch case (F1), and yes if HR looked and left it. Tried and kept safe, by reading:
amended, leave, approved request, confirmed, non-Administrator owner or editor, changed after 5
minutes, Absent with no comment, Absent with no punch.

**The Present row (engineer's soft spot):** safe, and not by luck alone. Both cancel branches
name the status, and the `linked` branch comes after the owner check. But the test proves less
than it seems, because `person_present` also has a person as owner. No fixture is protected by
the status rule alone. Add an Administrator Present with a free punch.

**2. Is the proof that the job made a row sound?**
- `AUTO_ABSENT_COMMENT` matches `shift_type.py:325` exactly. The "other half" and "threshold"
  comments do not match it, which is correct. **Proven.**
- Frappe writes this comment only after `mark_attendance` returns a row. So it is good proof of
  who made the row. It is not proof that nobody looked at it (F1).
- The skip comment goes through `frappe.bold`, and `LIKE %...%` handles the wrapper. The test
  uses Frappe's own function, so this part is real.
- **The English:** Frappe stores the translated text. If DTC's system language were not English,
  nothing would match, rows would be kept, and flagged punches would not count. That is the safe
  direction, but silent. **Not checked.** The test adds the Absent comment from the script's own
  constant, so it would not notice if the text drifted from Frappe's.

**3. Skip flag and undo.** The import's flag is correctly left alone. State is saved before the
first write. A crash between cancel and clear is safe, because a rerun works out the clear list
again. The problems are F3, F4 and m3.

**4. The ceiling.** Sound. I worked through a day shift, a window past midnight and a night shift:

| Time | Shift | Ceiling | Absent marked up to |
|---|---|---|---|
| 12:00 | 10-19 + 3 h | yesterday 22:01 | day before yesterday |
| 23:00 | 10-19 + 3 h | today 22:01 | yesterday |
| 23:00 | 12-22 + 3 h | today 01:01 | day before yesterday |
| 08:00 | 22-06 + 3 h | yesterday 09:01 | three days ago (night shift started then) |

- It never includes an unfinished shift, and Frappe waits a further day before marking Absent.
- **Shifts that were on:** no real change. **Shifts that were off:** now fixed.
- **Box unticked and old last sync:** refused, safely, and this now includes shifts only on old
  punches, so the operator may have to tick several.
- **It reaches past October.** Run on 3 Nov, it writes rows for the listed people for 1 Nov
  (a Sunday, so only if not a holiday for them), and for their November punches. These are days
  the job would mark anyway. Preview does not state the end date. P4.

**5. Order and promises.** Cancel, clear, retag, mark holds. Promises that hold: the cancel count,
the flag count, no-punch Absents untouched, kept days not cleared. Promises that do not: B1, F3,
"rebuild from the punches" (F1), the no-punch number (m1).

**6. The runbook.** Commands and names match the code. A non-programmer would be stuck at:
- step 8's refusal in B1, which has no entry;
- step 2 and line 16, "the number Surbhi approved", when no number exists until preview runs. It
  should say: read the list, approve it, then carry on;
- "both correct" in step 9 (F6);
- "a little higher" in step 7 (m6).

**7. Time and memory: not measured, no finding.** A preview with no list scans the whole company
three times, plus once for the list. With a list passed, also three times. **Inferred** for about
25,000 October punches (scaled from the 12 Oct count):
- Most of the work is on punches off their default shift, at about 5 queries each. If 1,500 such
  punches: about 30,000 queries, a minute or two. If every punch were off default: about ten minutes.
- Memory: tens of MB per scan.
- It only reads, so it should not block the live site.
- Run it inside `screen` so a dropped connection does not lose it. Reading the time of the next
  preview settles this.

**8. Tests that pass for the wrong reason.**

| Test | Problem |
|---|---|
| Lines 516-519, rebuilt status | **No test shift has a threshold.** So any punch set gives Present. The "too few hours" and "Half Day" outcomes never come from Frappe's job |
| Line 519, BDG4 d2 | Present from one punch; at DTC this is Absent (F4) |
| BDG5 d1, BDG6 d3 | Cancelled, but the rebuilt status is never asserted |
| `person_present` | Also protected by owner; the status rule is untested |
| Line 211, ceiling | Lower limit only. A version that returned today's unfinished shift at noon would pass. Assert the exact value |
| Line 542 | Sets the shift's last sync with the script's own `_ceiling`, then checks the script's own number |
| No fixture | B1, F2, F3, F5 |

**Tests that do catch things:** `bdg1_d3` (lines 450-451) fails if a no-punch Absent is cancelled.
Lines 448-449 fail if an import's flag is cleared. Line 578 is a real undo check. The refusal at
line 487 is real. Every `assertRaises` checks only for a `ValidationError`, not which refusal fired.

---

## 6. Commit's promises, one by one

| Promise | Result | Evidence |
|---|---|---|
| People with a job Absent/Half Day on a badged day are listed | Met | lines 392, 424 |
| Those rows are cancelled | Partial | F2 overreaches. F4 and F1 mean some rebuild the same |
| Frappe's flag cleared, import's left | Met | lines 369-377; test 446-449 |
| "A minute with two punches left alone" | Met, but too wide | F4 |
| Undo flags them again | Partial | m3 |
| Kept rows | Met, except F2 | lines 427-442 |
| "Made by a person" is kept | Met for what the row shows | F1, F2 for what it cannot show |
| Whole-company count | Met | line 572 |
| Midday ceiling fixed | Met | lines 204-210; table above |
| Refuses a ceiling before the period's end | Met | line 887; test 487 |

## 7. NFR and the seven dimensions

The budget has no row for a one-time script, and there is no impact analysis to compare with.

| Dimension | Before | After | Finding |
|---|---|---|---|
| Performance | Fine | Slower preview, read-only | Not measured; see question 7 |
| Security | No web door | Same | No new whitelist or `ignore_permissions`. Two `db.set_value` on punches, bench only |
| Reliability | Good | Worse at step 8 once the list grows | B1, F5 |
| Scalability | One company | Same | Not an issue at 468 |
| Maintainability | Long, one file | Longer, still readable | One-time script. See section 9 |
| Data integrity | Good | Better for the 27. New gaps | F2, F3, F4 |
| Compliance / privacy | Unchanged | Unchanged | No new personal data in the state file (punch names only) |

**The door, as the data-doors rule asks:** I traced this, not ran it. The file has no
`@frappe.whitelist`. Every step refuses anyone but Administrator (line 64). `test:186-196` covers
all eight steps. Nothing new can be reached from a browser. **Inferred**, not run on a site. This
script adds no limit on who sees data, so the rest of the door list does not apply.

## 8. Compliance

**Unreviewable against a spec:** this slice has no compliance section. What the code shows:

| Obligation | Mechanism | Test | Result |
|---|---|---|---|
| Accurate data before pay | Preview, keep rules | Partial | **Partial:** F1, F2 |
| HR's decision not overturned | Keep rules | Line 450 | **Partial:** F2 |
| Way back | Amend; undo for flags | Line 578 | **Discharged**, with m3 |
| Before and after recorded | State file only, deleted at step 10 | None | **Not discharged** (carried from 07) |

## 9. What to delete

- **The per-person no-punch count** (lines 564-570, 581-582): it drives nothing, it adds a query,
  and it holds the bug in m1. The real guard is `bdg1_d3`. Delete it, or make the one-word fix if
  Surbhi finds the number useful.
- **The second whole-company `_plan`** (line 572): with no list, `_derive_people` has just worked
  this out. Reuse it, and save one of the three scans.
- Nothing else. The new code carries the fix.

## 10. What was done well

- Clearing a flag only where Frappe's own comment proves Frappe set it. That keeps the 3,339
  flagged import rows out, which was the hardest thing to get right here.
- Saving the list of cleared punches **before** the first write.
- Separate counts for what will be cancelled and what will be kept, per person.
- Refusing a ceiling before the period's end, where the earlier code would have quietly marked
  almost nothing. That was a warning turned into a stop, in the right direction.
- A test that sets the clock to midday, and fails on the old code.

## 11. Confidence

- **High** on B1, F2, F3, F4 and m1: traced line by line. None run.
- **Medium** on F5 (the path is certain, how often it happens is not) and F6 (depends on whether
  ALV-211's days were re-marked).
- **Low** on size at DTC, for all of them.
- **Not checked:** the tests passing; DTC's system language; each shift's thresholds and windows;
  whether any step past preview has already run on DTC (the older version is on main); the two
  commits on `dev`.

## Questions

**Must know (these hold the verdict):**

1. **B1.** My reading: step 8 refuses if a kept day has an unlinked wrong-tag punch. I am unsure
   how many DTC has. It decides BLOCK or SHIP WITH FIXES. Question: is the count of such punches 0?
   Ranked P1 until someone counts, or the fix goes in, which is cheaper than counting.
2. **F1.** Does Surbhi accept that a one-punch day on a shift with no Absent threshold becomes a
   full Present? Ranked P2 until she says.

**Should know:**

3. **F6.** Were the ALV-211 late-out-punch days in October re-marked? And should an Absent holding
   a punch, with a later free punch, be rebuilt like a Half Day? The script keeps them. If she wants
   them fixed, that is a further rule. Ranked P2 for the wording only.
4. **F2.** How many declined requests cover a row on the CANCEL list?
5. Has pause or any later step already run on DTC? If so, preview will refuse the longer list, and
   the runbook's undo path applies first.

**Subtract pass.** I removed these after checking them:
- a queue flood on cancel (the 16 Oct trap was at 4,000 rows; this is a few hundred, with pauses);
- a "Left" employee failing the rebuild (`validate_active_employee` only stops Inactive);
- a punch pair across a minute boundary (the First and Last setting ignores pairing);
- Comment text being cleaned on save (the test goes through Frappe's real function);
- a `get_shift_details` trap at a last sync of 22:01 (traced, it lands on the right day).
