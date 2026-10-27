---
slice: 072-seats-follow-reporting
artifact: 06-review (senior architect review, change-process step 5)
author: hrms-technofunctional-reviewer
date: 2026-10-26
branch: slice/072-seats-follow-reporting, tip 72832964, on origin/dev 52fc3451 (merge base = 52fc3451, no merge commits)
status: advice - Surbhi decides. Nothing pushed, nothing edited in code.
---

# 072 · Senior architect review

## Verdict: SHIP WITH FIXES

The code does what Surbhi decided, and I found no leak and no wrong count. But two things are open:
one prototype difference that nobody approved (P2), and **I could not get a green Python run on my
own site** (see "What I could not check").

**Bad news first**

1. **My Python run on a fresh site did not pass.** On `test072_rev` (my own new site in
   `hrlocal-070s`), `test_reports_to_072` errored 7 of 7, `test_positions_064` 17 of 17 and
   `test_unseated_071` 12 of 12. `test_portal_security_010` (45 + 5) and `test_portal_split_034` (12)
   passed. Because the **unchanged base test** `test_positions_064` errors the same way, this looks like
   fresh-site setup (inferred: a fresh site with no `bench migrate`/fixtures), not this slice. My
   re-run to read the error hung for over 10 minutes and I stopped it, as the lead asked. **So the
   server tests are proven by reading only, plus the engineer's own run on `test070t` (7 OK).**
   Someone should re-run `test_reports_to_072` on a working site before the dev push.
2. **One prototype difference is not in the parity table** (M1 below).

## Blockers

None found.

## Majors

**M1 · P2 · Tray heading says "reports to Owner", the prototype says "set up under Owner".**
`portal.js` 3438-3441 (`posSeatSheet`). *Inputs:* Reporting lines, open the copy of Back Office under
the CFO. *What happens:* the tray's grey heading reads "HO · Acc · reports to Owner · HO" (seen in my
jsdom probe). The approved prototype (`prototype-v1.html` 565) reads "… · set up under Owner".
*Why wrong:* Surbhi's rule is that every difference from the prototype needs her yes; this one is
not in the parity table (spec §16) or the notes (D-1..D-5). It also says the opposite of the box she
just clicked: the box sits under the CFO, the tray says the seat "reports to" the Owner.
*Smallest fix:* in Reporting lines, use the existing `posParentWords(r)` with "Set up under {0}" in
that heading; or get her yes to keep it.

## Minors

**m1 · P3 · Tests do not cover AC-10 (ended or covering manager seat), AC-3 Inactive/Suspended, or
AC-67.** `test_reports_to_072.py`. The code is right by reading: an ended assignment is skipped before
the manager is counted (`register.py` 305-309), and only `status == "Active"` passes (307). A future
edit could break these unseen. Fix: two short asserts (Suspended manager; manager whose seat ended
yesterday).

**m2 · P3 · Code size is about three times the strategy's estimate.** The impact analysis said
"about 150 lines" (04, line 160); `portal.js` grew by 479 lines (about 420 code). The engineer said so.
Each piece is in the approved design (tray section, Find, paper walkers), so nothing to delete, but
Maintainability is "degrades" more than claimed.

**m3 · P3 · Paper: "None here: all N under …" prints even with Show Vacant off.** `portal.js`
`posWallCopy` (`more:`). Surbhi's decision covers "N open" following the tick; the spec's Q3 also
named "None here". I read it as a placement line, not a vacancy word, and keeping it avoids an
empty box with no words. Needs one line from Surbhi: keep as built (my recommendation) or hide.

**m4 · P4 · Tray names a seat in another company while the person is drawn at home.** Probe:
"Reports to N E-G (Group CFO)" for a Packing person drawn under Owner (Q6: no copies across
companies). True and in the reply, so not a leak; slightly confusing.

**m5 · P4 · Paper's Levels label "the N seats under it" counts copies as seats.**
`posWallLevels` adds `pl.under[r.id].length`. Footer and "below" count seat records correctly.

Nits (no action needed): the footer calls `posWallCount` twice; the 44 px rule for `.empty-state
.btn` on phones also touches "Build it from your people" (harmless); prototype prints "None here" in
italic `.vac`, build prints it in the grey line.

## Things I tried to break, and what happened

| Attack | Result | Label |
|---|---|---|
| Manager key: Left manager, other company, outside branch, unseated for owner, past/future date, Left person | Server sends id only if manager is Active and already in this reply; `""` HR only; nothing on non-today dates (`register.py` 461-488). Tests use marker values | Proven by reading; tests not green on my site |
| Branch argument narrows what may be named | `known` built from this reply's seats only | Proven by reading + test (e) exists |
| Loop P1→P2→P1 in two seats | One copy each way, both end boxes, drawing ends | Proven (tree check 22b) |
| Self-reporting; cycle inside one seat; person reporting to a seat-mate who is in a copy | All stay home, tray says "also in this seat" | Proven (my probe) |
| 60 names in one copy | 3 names + "+57 more here"; tray lists all 60 with lines; home says "60 more shown under Backoffice Executive" | Proven (my probe) |
| Manager's own seat emptied into a copy, with another copy hanging under it | Home drawn as "None here", copy hangs under it; never hidden | Proven (my probe) |
| Filters | Copies only of matching seats, only under kept seats; faded seats keep people home | Proven (22g, connector check) |
| Find to a copy, and to a seat whose home is hidden | Lands on the copy, path opened | Proven (22g) |
| Phone 390 px, no lines | Connector check 0 failures at 390, light and dark, incl. targets | Proven (ran it) |
| Connector rule | `FIXTURE=reporting check_positions_connectors.js`: TOTAL FAILURES 0 | Proven (ran it) |
| Wall chart: each person once, no leaks | 199 checks OK; sentinels absent, HR copy off and on | Proven (ran it) |
| All on A1 with copies | 8.5 pt (8.4 HR copy) | Proven (ran browser check) |
| Organisation page unchanged | `ocNodeCard` only adds pieces when `cls`/`quiet`/`empty` are set; pinned by 22d | Proven by reading + check |
| 071 merge in `check_positions_tree.js` | One chain `deleteChecks().then(unChecks).then(seats072)`; base runs 220 checks, branch 324 | Proven (ran both) |
| Hot files / incoming | 45 commits since af0b7cdf, all one author, no merge commits; the only removed lines in the check file are 071's old chain end | Proven |

## AC verification

| AC | Status | Evidence |
|---|---|---|
| AC-1..AC-7, AC-6b | Met by reading | `_add_managers`; `test_reports_to_072` (not green on my site) |
| AC-8 | Met (engineer's measure, 7 = 7) | Not re-measured by me |
| AC-9 | Met | `test_portal_security_010` 45 + 5 OK on my site; `ignore_permissions` untouched |
| AC-10 | Met by reading, untested | m1 |
| AC-11..AC-21, AC-65 | Met | tree 22a/22b, connector check run |
| AC-22..AC-26 | Met | 22a, probe |
| AC-27..AC-34 | Met | 22c, 22d, 22e |
| AC-35..AC-42 | Met, except tray heading wording (M1) | 22f, probe |
| AC-43..AC-48 | Met | 22g |
| AC-49, AC-50 | Met | marker checks 22c/22f; server tests by reading |
| AC-51 | Partial by design | 065 not landed (01c C3) |
| AC-52..AC-54 | Met | 22d |
| AC-55..AC-62 | Met; AC-57 see m3 | wall checks run |
| AC-63 | Met | 22h |
| AC-64, AC-66 | Met by engineer's one-off; connector 390 run by me | contrast not measured |
| AC-67 | By construction, untested | m1 |

## SEC / PRIV

| Item | Mechanism | Test | Status |
|---|---|---|---|
| SEC-1 | fail-closed `manager` | `test_reports_to_072` (a)-(g) | Discharged by reading; run not green on my site |
| SEC-2 | one key, literal key set, no new endpoint/write, Org card pinned | key-set test, 22d, CEILINGS | Discharged |
| SEC-3 | page reads only the reply; unknown ids never echoed | 22c/22f markers | Discharged |
| SEC-4 (a) jsdom oracle / (b) Playwright | independent oracle; connector check | 22a; run, 0 failures | Discharged |
| PRIV-1 (b) | copies built from assignments + `manager` only | 22d | Discharged; (a)/(c) wait for 065 |
| PRIV-2 | paper keys + `copy`, `same`, `more` | wall check, sentinels | Discharged |

## Non-functional, before vs after

| Dimension | Impact analysis said | I found |
|---|---|---|
| Performance | neutral, 7 → 7 statements | Join on the existing read; no new statement (read). Browser work linear |
| Security | neutral | Agree. No new endpoint, write or `ignore_permissions` |
| Reliability | neutral | Agree. Copies have no children, so no loop |
| Scalability | neutral | Agree (not measured at 10x by me) |
| Maintainability | degrades slightly (~150 lines) | Degrades more: ~420 code lines (m2) |
| Data integrity | improves | Agree: read every time, nothing stored |
| Compliance / privacy | neutral | Agree; owners see the link only when both people are on their page (Surbhi's yes) |

## Prototype parity, every difference

| # | Difference | Approved? |
|---|---|---|
| P-16/P-1/P-9 | "Reporting lines" name | Yes |
| P-22, P-23 | unseated name HR only; one "not on this chart" wording | Yes |
| P-25 | split advice gone in every view | Yes |
| P-27 / D-5 | "N open" on paper follows the tick, on every partly filled seat | Yes |
| D-1 | `""` HR only | Yes |
| D-2, D-3, D-4 | 11 px second line; "+M" overflow avatar; home keeps department | Pre-existing, listed |
| P-10 | preview side panel not built (stand-in) | Yes (spec) |
| **New: tray heading "reports to X · branch" vs "set up under X"** | M1 | **No** |
| New (nit): "None here" on paper in grey line, not italic | | No, cosmetic |
| New (nit): error heading has a full stop and no line break | matches AC-63 | spec wins |

## What to delete

Nothing. Every new function is used and in the approved design. I checked for a setting, cache,
field, flag or hook: none.

## What was done well

- One placement function (`posPlace`) for screen, tray, Find and paper, so they cannot disagree.
- The `manager` key fails closed on the server: an id only if it is already in the reply.
- The jsdom oracle is written independently of `posPlace`, and was shown to fail.
- Copies are end boxes, so a Reports To loop cannot hang the page.

## Confidence and what I could not check

- **Python server tests: not green on my own site** (fresh-site errors, also in the unchanged 064
  test; error text not read because the re-run hung and was stopped). Need: a re-run on a migrated
  throwaway site.
- Contrast in light/dark: not measured (no Python Playwright).
- Real DTC data (the 64, real A1 size): not checked; needs a dev run.
- Full `alvoraa_portal` suite: not run.

## Subtract pass

Removed from this review: a privacy concern about inferring a Suspended manager (the owner gets the
same words for a blank Reports To, so nothing can be inferred), and a filter "faded box with nothing
under it" note (AC-47 still holds).
