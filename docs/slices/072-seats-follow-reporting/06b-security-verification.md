---
slice: 072-seats-follow-reporting
artifact: 06b-security-verification
author: hrms-security-privacy-engineer
date: 2026-10-26
verified: branch slice/072-seats-follow-reporting, tip 72832964 (git diff origin/dev...HEAD), worktree 070-seats-reporting
site: my own throwaway site test072_sec in container hrlocal-070s (new-site + install-app, local only). test070t and test072_rev were not touched.
status: advice - Surbhi decides. No code edited. Nothing pushed.
---

# 072 seats · Security verification

**I wrote the 01c this checks (lesson 6).** The architect's `06-review.md` is the second pair of eyes;
SEC-1's rule and PRIV-1 are the two places to look at again if anyone doubts me.

## 1 · Verdict, first

**No blocker for the push to dev. Nothing private leaks in anything I could try.** All six
requirements are met or met-with-a-gap; the gaps are about proof, not about exposure.

| Gate | Blockers |
|---|---|
| Push to dev | **None from security.** One condition: the engineer's uncommitted review fixes (§6) must be committed with their tests green, because one new test errors today |
| Switch-on at DTC | 01c C2 (who has Read on `Alvoraa Position` at DTC) and C3 (merge with 065, re-run of the plan tests) are still open. C1 and C4 below |

## 2 · Surbhi's decisions, checked against the code

| Decision | Where it is enforced | Result |
|---|---|---|
| Owners and CXOs see the manager link | `register.py:485` sends the id to any reader when the manager is in the reply | Verified in code and by running it (owner test passes) |
| A blank Reports To goes to HR readers only | `register.py:476`, `:487` (`""` only when the reply holds the HR-only `unseated` list) | Verified by running it (owner reply has no `"manager": ""`) |
| Manager key only when the manager is already in the reply and both are Active | `register.py:303`, `:309`, `:481-485` | Verified by running it, including a runtime swap that removes the guard (§4, P9) |
| No copies across companies | `portal.js:1172` (`posManagerSeat` keeps only seats of the person's own company) | Verified by running it (probe: no copy id ends in another company's seat) |
| Plan keys absent for non-readers; copies never betray a plan | `posPlace` (`portal.js:1130`) reads only people, `manager`, type, weight and title | Partly: browser side verified; server side waits for 065 to land (C3) |
| Wall chart allowed-field copy (069 PRIV-1) holds with copies | `posWallCopy` (`portal.js:2856`) adds only `copy`, `same`, `more` | Verified by running it, HR copy off and on |

## 3 · Each requirement

| Req | Result | Mechanism (file:line at tip) | Proof |
|---|---|---|---|
| **SEC-1** manager key fails closed | **Met** | Person and manager status ride on the existing read through Frappe's link join, constant field strings (`register.py:298-303`). Rule in `_add_managers` (`:461-489`): today only (`:474`); person Active; manager Active and seated in this reply (`:309`) or in HR's `unseated` list (`:476-478`); `""` only for HR (`:487`); absent otherwise | `test_reports_to_072.py`, the 7 tests at the tip: **7 OK on test072_sec** (Verified by running it). My extra probe, 9 cases, all pass (§4) |
| **SEC-2** one key, no new door | **Met** | No new `@frappe.whitelist` (9 before, 9 after). `api.py` not in the diff. No new `gpFetch`/`frappe.call` in Positions code (the only added `gpFetch` mention is the existing `position_table` call behind Try again). `ignore_permissions` in `register.py`: **4 before, 4 after**; ceiling row unchanged (`test_portal_security_010.py:819`) | Literal key-set test passes; `test_portal_security_010` **45 + 5 OK** on my site; statements **7 at ~10 and 7 at ~200 seated**, reply 41,483 bytes (Verified by running it); Organisation card unchanged (`check_positions_tree.js:1356`) |
| **SEC-3** copies and tray name only what the reply holds | **Met** | `posParentWords` (`portal.js:1186`) says "a seat above your view" for a parent outside the reply; `posReportsLine` (`:3518`) names a manager only from `POS.rows` or `POS.unseated`; `posWhereItShows` (`:3486`) lists drawn boxes only | Tree check `:1339`, `:1417` pass. My probe: hidden seat id, unknown manager id and plan marker absent from chart, every tray (every seat and every copy opened), and Find; unseated manager named only when the list is present; every Show button points at a drawn box; seat titles and names holding `<img onerror>` show as text, never as an element |
| **SEC-4** no false line | **Met (CI part)** | `posPlace` (`:1130`), copies are end boxes (`posCopyNode` `:1205`, `child_count: 0`) | jsdom oracle written in the test, independent of `posPlace` (`check_positions_tree.js`, 324 checks pass); it notices a swapped manager (`:1276`). Runs in CI through `run_dom_tests.js` (15 run, 0 failed). Playwright half (b): **I did not run it** - engineer's notes record 0 failures, 8 with managers swapped |
| **PRIV-1** copies never betray a plan | **Partly met** | Placement never reads `plan`, `opening`, `leaving`, `hired_on`; the open slot and job opening stay on the home box | (b) passes (`check_positions_tree.js:1366`); my probe put a plan and a leaving date on a person drawn in a copy: neither appears for anyone. (a) and (c) need 065's code - **open, C3** |
| **PRIV-2** wall chart copy | **Met** | `posWallCopy` card keys: 069's list plus `copy`, `same`, `more` (seat titles and counts only). Tray layer is `display:none` on paper (`panels.css` print block); the view note is `noprint` | `check_wall_chart.js:547`, `:550` pass, HR copy off and on; every person prints once (`072 AC-55`); footer counts seats and people once. My probe: no manager id, unseated name, employee id, assignment id or hire date in the paper data; each person once, both modes |

## 4 · What I tried to break, and what happened

All on test072_sec or in jsdom on the page built from this checkout. Markers are invented.

| Attempt | Result |
|---|---|
| Owner (Positions Read, no HR role, branch A): read the manager of people whose manager sits in branch B, in another company, is Left, or is in no seat | Absent in every case; the ids and names are nowhere in the reply |
| Owner asks `branch=B`, and `branch=[A, B]` | Nothing from B is named |
| Store HR tied to branch A | Gets A's managers and A's unseated manager; nothing from B |
| Company-wide HR asks `branch=A` | A manager seated only in B is not sent |
| Manager Suspended / Inactive | Absent, for HR and owner |
| Manager whose seat ended yesterday | Absent for the owner; for HR only if the "in no seat" list holds them |
| Manager seated only from next week | Absent |
| Past date, future date, today written with a time | No key on past/future; today with a time behaves as today |
| Person Left but still seated | No key |
| Administrator (System Manager) | Every id sent was a person in the reply; no Left manager sent. Administrator's reply spans two test companies, so a manager seated in the second company's seat is sent - allowed by the rule, and the page still hangs no copy across companies |
| **Remove the "in this reply" check at runtime** (monkeypatch, no file edited) | All 4 markers leak (unseated id, other-company id, Left manager, other-branch manager). With the real rule, 0. The guard is what stops it |
| Tray, "Where it shows", Show buttons, Find, outline on hover | No marker, no name outside the reply, every target a drawn box |
| Wall chart print and Ctrl+P | Paper data holds only allowed keys; tray lines never print; each person once |
| Browser history, storage, page or PDF title | The diff adds no `pushState`, `replaceState`, `localStorage`, `sessionStorage` or `document.title`. Copy ids are seat ids only and never reach a URL. The print title still matches 069's pattern with no name (`check_wall_chart.js` AC-38 passes) |
| Planned person (065) | Browser side only (above). The server and browser plan tests cannot run until 065 lands |

**What must exist for the controls to show on real data (lesson 1).** DTC has one company and no
branch-limited HR, so the cross-company and store-HR cases cannot appear there. Only DTC's two
branch-limited owners exercise "manager outside my scope". So a clean DTC screen proves nothing; the
CI tests build every case themselves.

## 5 · Findings

No Blocker. No P0 or P1.

| # | Rank | Finding | Fix |
|---|---|---|---|
| F1 | Minor · P3 | **The first run of `test_reports_to_072` on my brand-new site errored 7 of 7** (after 8 s). Every later run passed. I did not keep the error text. CI also starts from a fresh site, so SEC-1's gate is only proven once it runs green there | Read the first CI run of this file. If it errors, the fixture needs a record a fresh site lacks. *Unknown*, not an exposure |
| F2 | Minor · P3 | The spec traces proposals `pSEC-1/2`, `pPRIV-1/2/3`, not 01c's `SEC-1..4`, `PRIV-1..2` (`03-functional-spec.md:244-248`, `:689`). The coverage is there; the ids do not match | Analyst adds the 01c ids to the trace table |
| F3 | Minor · P4 | SEC-1's test has no System Manager reader, which 01c asked for. My probe covered it (passes) | Add one System Manager case |
| F4 | Minor · P4 | PRIV-2's `MGR-SNTL` person is drawn in a home box, not in a copy as 01c asked. All other sentinels are on copy people, and my probe covered a copy person | Move the marker onto a person drawn in a copy |

**Worries (not findings):** none new. R2 (Organisation page still hangs people by seat) and R3 (a
leaver can stay seated) from 01c are unchanged by this slice.

## 6 · Work in progress seen during the check

From 02:02 UTC, while I was checking, the engineer edited `portal.js`, three test files, a check
script and the notes, without committing (review fixes M1 and m3, and new tests). `register.py`
was not changed. I re-ran the browser checks and my probe on that working tree: tree 325 checks, wall
chart 200 checks, probe 30/30 - all pass. The two `portal.js` changes are neutral or safer for
security (the tray now uses `posParentWords`, which never names a parent outside the reply).

**One new server test errors:** `test_a_manager_in_a_current_covering_seat_is_sent` fails inside the
fixture's `assign` helper (`test_org_structure.py:100`), not in the rule. The engineer is editing
that helper. It must be green before the push.

## 7 · Switch-on at DTC

| # | Check | State |
|---|---|---|
| C1 | SEC-4 (b) Playwright on the census-shaped fixture | Recorded by the engineer (0 failures). I did not re-run it |
| C2 | List roles with Read on `Alvoraa Position` at DTC | **Open. I could not check that** - needs read-only access to DTC's Role Permissions |
| C3 | After 065 merges: 065's byte-for-byte test with `manager` keys, and the plan-words browser check with copies on the page | **Open** |
| C4 | The served `portal.js` holds the 072 code (deploys do not refresh assets) | Open until deploy; DevOps check |

## 8 · Compliance

| Obligation | Checked | Result |
|---|---|---|
| DPDP Act 2023 and Rules 2025: safeguards, purpose limitation | Baseline verified 24 Aug 2026 (63 days; stale from 22 Nov 2026) | Met: the link goes only where both people are already on the reader's page; nothing stored, logged or cached |
| OWASP ASVS 5.0 L2 access control | Baseline §5 | Met: same Read check and scope as before; no new door |

## 9 · Residual risk

| # | Risk | Label | Owner | Accepted |
|---|---|---|---|---|
| R1 | Owners learn the Employee-record manager of people whose seat disagrees (88 of 361 at DTC on 24 Oct) | Intentional trade-off | Surbhi | Yes - her decision that owners and CXOs see the link (date as given in the brief to me, 26 Oct 2026) |
| R2 | Organisation page still disagrees with Positions for those people | Temporary debt - removed by a later slice | Surbhi | **Waiting** |
| R3 | A leaver can stay seated and still be drawn | Temporary debt - removed when leaving ends the assignment | Surbhi | **Waiting**, open since 064 |
| R4 | The reply sends a parent seat's id even when outside the reader's view (`register.py:392`); 072 never shows it | Acceptable simplification, P4 | Surbhi | **Waiting** |
| R5 | The real-browser "no false line" proof is not in CI | Intentional trade-off | Surbhi | **Waiting** |
| R6 | SEC-1's gate not yet seen green on a fresh CI site (F1) | Temporary debt - removed by the first green CI run | Surbhi | **Waiting** |

None is dangerous debt.

## 10 · What I could not check

- The error text of F1's first run (not kept). Needs: the first CI run, or another fresh site.
- C2 at DTC - needs read-only access to DTC's role permissions.
- 065's plan tests - need 065's code merged with this.
- Playwright checks - not installed where I ran.

## 11 · Clean-up

My site test072_sec and the folder `/tmp/sec072` (probe files and logs) are still in hrlocal-070s.
Drop the site when the slice is done; nobody else uses it. During the check I briefly put my probe
file into the bench's shared Python folder by mistake; I removed it after the run (verified: 0 files).

## Subtract pass

Removed: a planned re-run of the whole `alvoraa_portal` suite (the engineer already ran it; the
modules that guard this slice were enough), a section restating 01c's threat model, and a fifth
minor finding about wording in the view note (not a security matter).
