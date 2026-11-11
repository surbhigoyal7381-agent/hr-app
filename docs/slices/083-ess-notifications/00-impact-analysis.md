---
slice: 083-ess-notifications
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-11-11
status: for Surbhi — strategy gate. No code written. Seven ⚠ DECISION rows, two of which
        change a line the design asked for.
inputs: [02-functional-spec.md, 01-product-brief.md, 01b-ux-design.md (approved 6 Nov 2026),
         01c-security-privacy-requirements.md, 07-devops-inputs.md §1–§3, 08-dtc-counts.md,
         prototype-v1.html, .claude/context/change-process.md, no-over-engineering.md,
         data-doors.md, parallel-work.md, frappe-conventions.md, nfr-budget.md,
         security-compliance-baseline.md]
ticket: ALV-322 (Epic)
worktree: .claude/worktrees/083-ess-notifications · slice/083-ess-notifications · origin/dev 814d540f
---

# 083 · Impact analysis and strategy

## Answer first

**The slice is buildable as specified, on rung 4, in six files. I found five things in the
code that change what the spec asks for, and two of them change a line the design
approved.** None of the five is a reason to stop; all five are cheaper than what was
written down, and each needs one word from Surbhi so I am not quietly redesigning an
approved screen.

**The five, shortest first:**

1. **`--on-primary` does not exist.** The design (N3) asks the badge's digits to use a
   token that is in no file in this repository. I do not need to add one: `--primary-lt`
   already moves in step with `--primary` in both themes **and** through the tenant brand
   clamp, so `background: var(--primary); color: var(--primary-lt)` passes 4.5 : 1 in all
   four theme × brand combinations with **zero new tokens and `design_system.html`
   untouched**. ⚠ **DECISION E-1.**
2. **`12px` is already one of the portal's seven allowed font sizes**, so AC-52 is free.
   But the CI gate `check_design_system.py` is at **7 of 7** on this page, so **any other
   new pixel font size in this slice fails CI**, and every new colour must be a `var()`
   (`loose_colours` limit is 0). This is a hard constraint on the whole page build, not a
   note.
3. **AC-12 as written cannot be met.** It asks for one badge function called from exactly
   three places. `ntPaintBadge` has **four** call sites today, and the merged number needs
   a repaint wherever **either** half changes, which is six places. The *intent* — one
   place computes the number — is met by making the function take no argument and read
   two stored values. ⚠ **DECISION E-2.**
4. **The bulk mark-as-read cannot simply be "extended in place".** `notices.py` imports
   `grooming`, so `grooming.py` cannot import `NOTICE_DOCTYPES` back at module level. I
   recommend **moving** the function to `notices.py` and deleting it from `grooming.py`:
   net **zero** new whitelisted endpoints, the doctype list stays single-sourced, and it
   lands in the file whose docstring already owns notices. It costs one line in an
   existing test file. ⚠ **DECISION E-3.**
5. **The desktop bell cannot be covered by the jsdom tests if it lives in Frappe's
   navbar**, because the page is `{% extends "templates/web.html" %}` and the jsdom
   harness expands only our own includes. My answer is to declare the bell in **our**
   `frame.html` (so CI sees it) and move it into the navbar at boot if the navbar is
   there, with our own CSS position as the fallback. ⚠ **DECISION E-4.**

**Where I am on the cost ladder.** Rung 4 (new code in existing files) for the page, the
badge and the desktop bell — rungs 1 to 3 were rejected because no Frappe or ERPNext
screen gives an ESS employee a notifications page, and Frappe's own Notification Log list
is a Desk screen that ESS staff cannot reach. **Rung 1** for the rate limit (an existing
decorator, one line) and **rung 1–2** for the bulk write (an existing function, moved).
**No new DocType, no new field, no migration, no new web address, no new dependency, no
new container, no job, no timer, no cache.** `deploy/nginx.conf` is untouched.

**The one number that worries me** is not in the spec: DTC holds **zero** rows of all
three notice kinds and **902 unread `Employee` rows** that this page must never clear. So
on day one at DTC the notices half of this page is empty and the only assertion with real
data behind it is the one that proves we did **not** touch those 902 rows (AC-31).

---

## 0 · Parallel-work check

`git fetch origin` at 2026-11-11. **`HEAD..origin/dev` is empty — nothing came in.** The
worktree sits on `814d540f`, the same commit `origin/dev` points at.

**Worktree:** `.claude/worktrees/083-ess-notifications`, branch
`slice/083-ess-notifications`. The shared checkout `C:/Surbhi-Git/hr-app` is **not** mine
to edit and holds **49 modified files belonging to other sessions** — among them
`auth.py`, `hooks.py`, `hr_api.py`, `inbox_api.py`, `payroll_rules.py`,
`public/js/ess/next-inbox.js`, `public/css/ess/frame.css` and
`public/css/ess/panels.css`. **Two of those are files I need** (see the clash row below).

**The work board** (`.claude/work-in-progress.md`) shows three live rows: ALV-318/319
(joiner role), ALV-281 (history leak), ALV-326 (shift hours — strategy only). **None of
them touches a file I touch.** `git worktree list` shows 140-odd worktrees; I am claiming
no one else's.

### Files I will change, and who else is in them

| File | Hot file? | Who else is in it | The plan |
|---|---|---|---|
| `alvoraa_portal/alvoraa_portal/notices.py` | no | nobody — no board row, no incoming commit, not modified in the shared checkout | mine |
| `alvoraa_portal/alvoraa_portal/grooming.py` | no | nobody. ALV-326 names `day_marks.py`, not this | mine (one function removed) |
| `public/js/ess/portal.js` | **yes** — the most-changed file in the repo | **not** modified in the shared checkout today. ALV-326's row names `portal.js (dmWhere only)` — a different block, and that slice is strategy-only with no code | **Split.** My work is one new block with the prefix `nf`, plus named edits inside the existing `hm`/`nt` block (lines 6540–6910). I touch nothing else, move nothing, re-indent nothing |
| `templates/includes/ess/frame.html` | **yes** | nobody today | **Split** — the bell block and one new nav item, appended inside the existing nav list; no existing line moved |
| `templates/includes/ess/parts/notifications.html` | new file | — | mine |
| `public/css/ess/panels.css` · `frame.css` | **yes** | **⚠ both are modified right now in the shared checkout by another session** | **Sequence.** I write my CSS in my worktree as an appended block with the `nf-` prefix plus the one existing `.notif-badge` rule. Before I bring anything into local `dev` for a bench run I will re-read those two files in the shared checkout and tell Surbhi if the other session's change overlaps `.notif-badge` or the `.mob-header` media query. **I will not stage, revert or tidy their lines.** |
| `alvoraa_portal/alvoraa_portal/www/hrms-employee.html` | yes (one line) | nobody today | one `{{ ess_part("notifications") }}` line, appended |
| `alvoraa_portal/tests/portal_home_076_test.js` | existing test | nobody | **one assertion changes** (see §3). Flagged loudly because it is slice 076's own pin test |
| `alvoraa_portal/alvoraa_portal/tests/test_notices_076.py` | existing test | nobody | the ≤ 12 ceiling becomes ≤ 14; **the flatness line is not touched** |

**Bench:** `hrlocal-bench` is up and shared; `hrlocal-326*` containers belong to ALV-326.
I ran **no** bench command, opened no site, changed no record. The two `docker exec` calls
I made were `grep`/`sed` inside the already-running container's **app folder** to read
Frappe's own source. Nothing was written anywhere.

**The pin tests that stop my features being dropped by someone else's merge** are listed
in §10.6. Every feature in this slice gets one.

---

## 1 · Cross-module reach

| App / module | What this slice does to it | Risk if I am wrong |
|---|---|---|
| **`alvoraa_portal`** | all of the work: `notices.py` (two keys on one return, one function moved in), `portal.js` (new `nf` block, edits in the `hm`/`nt` block), `frame.html` (desktop bell, one nav item), a new part file, `panels.css` / `frame.css`, one line in `www/hrms-employee.html` | the whole slice lives here |
| **`alvoraa_portal.grooming`** | `my_notices_seen` **moves out** (⚠ E-3). `_readable` is called with a longer list — **the same number of queries**, because it has no per-row query (verified in source: at most two document reads, one `_active_employee`, one manager read, one `hr_scope`, all on `IN` lists) | a dropped filter term in the moved write; a second `_readable` call if I fold badly, which would break the ≤ 14 ceiling |
| **`alvoraa_portal.inbox_api`** | **read only, not edited.** `get_nav_counts` gains its first live caller; `get_inbox` keeps its Home caller. `ROW_KEYS`, `APPROVAL_PARTS` and every per-part scope are untouched | if the bell ever called `get_inbox` instead, every page load would carry colleague names — OPS-1. My code calls `get_nav_counts` and the test asserts it |
| **`hrms`** | **nothing changed.** Leave Application, Expense Claim, Attendance Request, Shift Request rows arrive through `inbox_api`'s existing scope | — |
| **`erpnext`** | **nothing changed.** `Employee.status` is read by the existing scope helpers | — |
| **`frappe`** | **nothing changed, and no upstream file edited.** `Notification Log` is read with `frappe.get_list`, counted with `frappe.db.count` and written with `frappe.db.set_value`. Frappe 16.33.1, verified in the container | a `Custom DocPerm` would be an upstream-adjacent change — refused in 01c R3, and I am not adding one |
| **`alvoraa_goals` / `alvox_compensation`** | **not touched.** Goal and KPI rows reach the page only through `inbox_api`'s existing `goal_updates` part | — |
| **New app** | **none** | — |

**The phone:** nothing. Mobile is a PWA over this same portal (Surbhi, 24 Oct 2026). No
Flutter work, no mobile artifact, no store step.

---

## 2 · Every caller of every function I change

Grepped across `alvoraa_portal`, `hrms` and `scripts` for `.py`, `.js`, `.html` and
`.json`, excluding the discarded `next` redesign.

| What I change | Every caller today | What I must not break |
|---|---|---|
| **`notices.notices_feed`** (two keys added; existing keys unchanged) | `portal.js:6814` (Home's notices card), `6837` (`ntBellBoot`), `6875` (`ntOpenAll`); `tests/test_notices_076.py` (10 tests), `tests/test_announcements_076.py:482, 880`, `tests/measure_076.py:48, 115` | the existing key set, plus `capped`. `test_the_person_sees_their_own_unread_notice_with_a_fixed_set_of_keys` asserts the key set exactly and **must be extended, not loosened** |
| **`grooming.my_notices_seen`** (moved to `notices.py`) | **no live caller.** `portal.js:15487` names it inside the `WRITE_CALL` regex; `tests/test_grooming_066.py:999` calls it directly | the regex entry becomes dead configuration once the function moves. `^mark(_|$)` already matches the new name, so I remove the special case in the same commit and say so. The test moves with the function |
| **`grooming._readable`** (called with more rows; **not edited**) | `notices.py:74`; `grooming.py:1023` (`my_notices`) | the hiding behaviour that `test_a_notice_is_hidden_when_its_reader_may_no_longer_read_the_mark` proves — unread goes 1 → 0 with no row changed |
| **`ntPaintBadge`** (signature changes — ⚠ E-2) | `portal.js:6816`, `6839`, `6877`, `6903`; named in a comment at `frame.html:134` | the `99+` rule and the `display:none` at zero, both already there |
| **`hmPaintPending`** (the chip's definition changes) | `portal.js:6554`, `6807`, `11354` | the CXO path, the five-row cap, the footer, the empty state |
| **`homePending` / `homeNotices`** (unchanged, re-read) | `6559`, `6562`, `6568`, `6569`, `8763`, `8764`; `tests/portal_home_076_test.js:98` asserts both exist on `window` | they must stay global and keep failing quietly |
| **`ntOpenAll`** (keeps working; the bell now opens the page instead) | `6873`, `8349` (`data-hm="note-all"`), `18366` (`toggleNotifPanel`) | Home's "See all" button keeps the sheet. **Only the bell's destination changes** |
| **`mayOpenPanel` / `switchPanel`** (**not edited**) | `routeFromAddress` (`4723`), every nav item, `tests/portal_routing_288_test.js` | `switchPanel` does an unguarded `getElementById("panel-" + name)`, so the panel markup **must** exist or every route to it throws |
| **`.notif-badge`** CSS rule | `frame.html:137`; `tests/portal_home_076_test.js:247, 260` | the badge must still be hidden at zero |
| **`#mob-notif-btn`** | `portal.js:6826`; `frame.html:135`; `tests/portal_home_076_test.js:248` asserts the accessible name is exactly **"Notices, 3 unread"** | **this assertion changes.** See §3 |

**Nothing in `hrms` or `erpnext` calls anything I touch.** `get_nav_counts` has no caller
at all today, which is why part 3 is a new request on every non-Home page rather than a
switch being flipped.

---

## 3 · Home's "Pending for you" chip — the blast radius

This is the only live, shipped number this slice changes, and Surbhi asked for it by
name. Here is every place that paints it, reads it or moves it.

| # | Where | What it does today | After |
|---|---|---|---|
| H-1 | `portal.js:6655`, inside `hmPaintPending` | **computes** `total` = `d.total − shift_requests` for an ordinary person, or the sum of kind counts for a CXO | the shared **work-owed** sum: every `parts[]` count except `shift_requests` **and** `my_requests`. The CXO path is unchanged |
| H-2 | `portal.js:6656` | paints `#home-pending-chip` as "{total} waiting" | same words, new number |
| H-3 | `portal.js:6660` | draws the first 5 of `HM.rows`, which **includes the person's own requests** | the card splits: approval and policy rows first, then **a sub-heading** "Waiting on someone else · not counted — nothing for you to do yet" with the own-request rows under it (AC-22) |
| H-4 | `portal.js:6662–6666` | the footer says "Showing 5 of {rows.length}" and "See all {total}" | **these two numbers stop agreeing** the moment own requests leave the count: `rows.length` includes them, `total` does not. The footer must count only the rows above the sub-heading. **This is the quiet break nobody wrote down** |
| H-5 | `portal.js:6672`, `hmPendAll` | the "See all" sheet says "Showing all {rows.length}" | same split applies |
| H-6 | `portal.js:6798–6807`, `hmDropPending` | decrements `p.count` **and** `d.total`, then repaints | still correct: the work-owed sum reads `p.count`, so it falls by one without `d.total` mattering. **`d.total` stops being read by the chip**, which is the point |
| H-7 | `portal.js:11354` | `if (HM.pend) hmPaintPending();` — a repaint after roles land | unchanged, and it now repaints the badge too |
| H-8 | `portal.js:6566`, `hmRefreshIfStale` | re-asks both feeds when you come back to Home after a minute | unchanged. **Still navigation-triggered, still no timer** (OPS-27) |
| H-9 | `parts/home.html:44–50` | the card's markup: `home-pending-chip`, `-body`, `-foot` | one sub-heading element added inside `-body`; no id renamed |
| H-10 | `portal.js:6780–6784`, inside `hmDecide` | hand-decrements **`sb-team-badge`**, a different badge (Team View) | **untouched.** Naming it so nobody confuses the two |
| H-11 | `frame.html` — `sb-leave-badge`, `sb-goals-badge`, `sb-policies-badge`, `sb-dr-badge`, `sb-team-badge` | five sidebar badges painted only after their own panel opens; `get_nav_counts` had no caller | **out of slice** (PM-8, Surbhi's decision). **Say it out loud: after this slice the bell is visibly more trustworthy than those five, and a sharp user will notice** |
| H-12 | `tests/portal_home_076_test.js:132, 181, 302` | asserts the chip reads "6 waiting", "1 waiting", "1 waiting" | **all three still pass**, because every fixture sets `my_requests` count to 0. So **the existing test does not pin this change at all** — I must add the case it is missing |

### What proves Home and the bell cannot drift apart

Three things, in order of strength:

1. **One function, one definition.** `ntWorkOwed(d)` takes either payload — `get_inbox`'s
   or `get_nav_counts`' — because **both return the same `parts[{key, count}]` shape**
   (verified: `inbox_api.py:1138` and `:1181`). Home's chip, the bell and the new page's
   group-1 heading all call it. There is no second expression anywhere that adds counts.
2. **AC-23's test**: paint Home and the bell from one payload and assert the two rendered
   numbers are equal — including a fixture with `my_requests` **greater than zero**, which
   is exactly what today's test lacks (H-12). Without that fixture the test passes on a
   coincidence.
3. **A source assertion** that `#notif-badge`'s text is written in **one** function, and
   that `d.total` and `approvals_total` appear in no badge or chip expression. Those are
   the two wrong answers the spec names (AC-11), and a grep is the cheapest guard against
   either coming back.

### The one existing assertion that must change

`alvoraa_portal/tests/portal_home_076_test.js:248`

```js
eq($("mob-notif-btn").getAttribute("aria-label"), "Notices, 3 unread",
   "the bell's accessible name carries the number");
```

The approved design replaces that name with **"Notifications, 7 waiting"** (01b §6.1).
So this line becomes `"Notifications, 3 waiting"`. **Its intent survives and I will not
weaken it:** the assertion still proves the accessible name carries the number, and I add
a second one proving the number is work **plus** notices. I am flagging it because it is
slice 076's own pin test and a silent edit to it is exactly what `parallel-work.md` §7
exists to prevent.

---

## 4 · Persona impact

| Persona | What changes | What does not |
|---|---|---|
| **Employee** (desk) | a bell with a number on every screen; a page with their own 30 days of notices and their own open requests at a durable address; Home's chip no longer counts their own requests, so **an employee with one pending leave request sees a smaller number than yesterday** — moved, not lost, to a named sub-heading | what they may see. Entitlement widens by nothing |
| **Frontline employee on a shared handset** | the same page, work first, three chips in one row at 390 px, **no fourth bottom-bar item**, nothing cached, nothing in browser storage. The bell stays 44 px | the risk I cannot close from a desk: Chrome Android's back/forward cache after sign-out (R5, AC-63). **That is a release gate, not a build item** |
| **Line manager on a laptop** | the thing the slice is for: a signal on every screen, and approve/decline from the page through the sheets they already know | their scope. The named-approver filter is `inbox_api`'s and I do not touch it |
| **HR Manager** | five rows per group with the real total named; "Mark all as read"; a true unread count instead of a capped one. Rows stay inside `permitted_companies` | **no HR variant of the page.** One page for everyone (brief §5.13) |
| **CXO (System Manager)** | one row per kind, counts only, badge = kinds + unread, so the number is 1–5 and moves when a queue empties | **no colleague names in a bell payload**, because the bell takes `get_nav_counts` and never `get_inbox` |
| **Platform operator with no Employee record** | `notices_feed` works; `get_nav_counts` returns `has_employee: false` and empty parts; badge is their unread notices only | no colleague data of any kind |
| **A leaver whose login still works** | nothing. `_active_employee`, `hr_scope` and `_my_employee` all filter `status = "Active"` — three separate places, verified | — |
| **Guest** | nothing. `/hrms-employee` redirects before any context is built | — |

---

## 5 · HRMS domain impact

| Domain | Impact |
|---|---|
| **Leaves** | approval rows are **drawn and decided** through the existing sheet and the existing `action_leave` endpoint. No leave arithmetic, no balance, no allocation, no policy touched. `half_day`, `lwp_in_play` and `lwp_limit` reach the sheet exactly as they do from Home today |
| **Attendance** | correction rows are drawn and navigated to; `attendance_correction`'s own review screen decides them. No punch, no shift, no day mark touched |
| **Payroll** | **not involved.** The only pay-adjacent values are `lwp_in_play` / `lwp_limit` on a leave row where a pay rule set is on, and they are read, not written |
| **Appraisals, goals and KPIs** | goal and KPI rows are drawn; their existing drawers decide them. No scoring, no ranking, no rating |
| **Org structure** | read only: `reports_to` decides whose grooming notice is readable (`_readable`), and `permitted_companies` decides an HR Manager's rows. Nothing writes to either |
| **Learning / recruitment** | not involved |

---

## 6 · Races, edge cases and state — settled before any code

Named here because they decide the shape, not only the tests.

**Races.** *Two approvers on one leave application:* the existing endpoint refuses the
second; the page shows **"Already decided by someone else."** and removes the row (AC-45).
Nothing in my code decides anything. *"Mark all as read" while a single notice is being
marked read:* both set `read = 1` where `read = 0`; the second matches nothing. Safe to
run twice, so a retry cannot double-post. *Two handsets clearing at once:* same.
*`hmDropPending` firing while a refresh is in flight:* the refresh replaces `HM.pend`
wholesale and repaints, so the worst case is the decided row reappearing for one paint and
leaving on the next — today's behaviour, unchanged. *A bulk clear landing between the
badge's two calls:* the badge is painted from whichever answers; the next navigation
corrects it. No timer means no window where a stale number sits unrefreshed on screen
while the person watches.

**Edge cases.** None / one / many: zero rows gives five separate empty states (AC-41 to
AC-44); one row draws no footer; 150 unread gives 100 rows, a true count of 150 and the
capped line. No `waiting_since` → the row draws **without** the waiting line, never
"waiting undefined days". A notice whose document was deleted → `_readable` drops it and
the count drops with it. A manager's mark notice is readable **only on the mark's own
day** — so the same person's badge legitimately falls overnight with no row changed, and
the count must be computed through `_readable`, never as a plain `COUNT(*)`. A mid-month
joiner with nothing at all → the first-morning box. A cancelled or amended application →
the row is simply no longer in the queue. 200 % text at 360 px → chips wrap; nothing is
`nowrap`.

**State transitions.** There is exactly one state machine and Frappe owns it:
`Notification Log.read`, `0 → 1`, by the recipient only, terminal, **no "mark unread"**,
and **no notification is sent by this slice at all**. Work owed has **no state in this
slice** — it leaves the list for four reasons and three of them have a sentence (done /
decided elsewhere / withdrawn), while the fourth, "it stopped being yours", says
**nothing**, because "you no longer approve for Rakesh" leaks an org change. **The
transition the spec does not name** is a notice whose row still exists but whose document
became unreadable *between* the page's read and the badge's count. Both go through one
`_readable` call on one payload, so they cannot disagree — that is a reason to fold the
count into the existing call rather than add a second one.

---

## 7 · The seven non-functional dimensions — a verdict on each

| Dimension | Verdict | The argument |
|---|---|---|
| **Performance** | **degrades, measurably and acceptably** | Honest: **+21 statements and 638 bytes on every non-Home page load**, because `get_nav_counts` has no caller today. `notices_feed` goes from ≤ 12 to ≤ 14 statements, both of them flat in headcount. Measured p95 across these calls is **215 ms** against a 500 ms budget (slice 044, Sep 2026, fixture sites). At DTC that is an estimated 134,000 extra statements a day — under one extra call a second even in the 11 AM punch quarter. Set against it: the page itself is ~235 KB gzipped and this slice adds **~8–12 KB cold, ~600 B warm**. **No timer, no polling, no cache** — the one change that could multiply this tenfold is a `setInterval`, and it is banned by AC-64 with a source assertion behind it. The flatness gate `small.n == big.n` is **not** touched |
| **Security** | **improves** | Two unprotected tools gain a tested contract. `frappe.db.count` applies **no** permission condition (verified in `database.py:1285`: a plain `COUNT(*)` through the query builder) and `frappe.db.set_value` with a filter dict issues **one direct `UPDATE`** that checks nothing (verified at `database.py:934–1001`). So the `for_user` and `document_type` terms are the whole control — and AC-30/31/32 are three separate assertions written to fail when either term is removed. Against that: this slice adds **one** new whitelisted endpoint and removes one, so the count does not grow; `ignore_permissions` stays at 0; no raw SQL; no client-supplied doctype, field, user or filter; the write is POST-only and rate-limited |
| **Reliability** | **improves slightly** | Each call fails on its own and leaves the badge exactly as it was — the existing `ntBellBoot` behaviour, kept and extended to both calls. One failing part of `get_nav_counts` cannot take the page down (ALV-250's fix is in `inbox_api`, untouched). The write is safe to run twice. **A spinner always ends** — replaced by rows, an empty box or an amber box. Three refusals reach the person as sentences, never a stack trace and never "check your connection". Against it: the bell now depends on **two** calls instead of one, so the failure surface widens — which is why neither failure is allowed to blank anything |
| **Scalability** | **neutral** | Nothing here grows with headcount. Both new statements are flat: the announcement count is one `COUNT` on the `for_user` index, and the unread grooming read folds into the **same** `_readable` call, which asks a fixed number of queries whatever the row count — longer `IN` lists, not more queries. The page caps at 100 notices and 50 rows per part and **says so on screen**. The cost grows only with one person's own total row count, and the only usable index is `for_user` alone (`read` and `document_type` carry none) — at DTC's heaviest, 169 rows, that is nothing. **No composite index**, because no measured number misses the budget |
| **Maintainability** | **improves, narrowly** | Deletions beat additions in three places: the bulk write stops being a dead endpoint in the wrong file, the `WRITE_CALL` special case for it goes, and the badge stops having two expressions for one number. Against it: `portal.js` grows by an estimated 450–700 lines, and it is already 24,124 lines and the most-changed file in the repository. I keep that cost contained with one block, one `nf` prefix, and no edit outside the lines named in §2 |
| **Data integrity** | **improves** | The headline fix: today `unread` is counted from a list capped at 100, so a badge can say 99+ and never clear. After this it is the true count, through the same readability gate as the list, so **the count equals the list it links to** — `inbox_api`'s first rule. `capped` says when the list was cut, matching what `get_inbox` already returns per part. **No cache, so nothing can be stale**; the badge falls the moment a decision lands, because the sheet already decrements the row. One risk I am naming rather than hiding: the bulk write uses `update_modified=False`, so **nothing records when a bulk clear happened**. The data is not decision-bearing and the spec accepts that gap (§14); it is a gap all the same |
| **Compliance / privacy** | **neutral on entitlement, one real change in exposure shape** | Nothing new is collected, stored, copied, logged or exported. No new field, no new DocType, no read receipt, no per-recipient read state to anyone but the recipient. Every field drawn is already in `ROW_KEYS`, and `explanation` — the free-text absence reason — is **not** in it. What genuinely changes: **30 days of one named person's HR messages become a durable, bookmarkable page two taps from any screen, on handsets 441 DTC staff share.** The controls are the session, `Cache-Control: no-store`, no client storage, a no-op service worker and a route with no identifier in it. The last link — Chrome Android's behaviour on Back after sign-out — is **unproven and a release gate** |

---

## 8 · How each requirement will actually be met

### Security (01c §9)

| ID | Where it is met | The mechanism |
|---|---|---|
| **SEC-1** | `notices.py`, the new count | Both statements carry an explicit `for_user: frappe.session.user` **and** `document_type` term. No `frappe.get_all` for the counted set; the grooming half goes through `grooming._readable`. Nothing comes from the client. Test asserts A's count equals A's own readable rows **and** is strictly less than the site-wide count, plus a source assertion that the filter dict holds `for_user` |
| **SEC-2** | `notices.py`, `mark_all_seen` (moved from `grooming.py`) | **One** `frappe.db.set_value("Notification Log", {"for_user": <session user>, "read": 0, "document_type": ["in", NOTICE_DOCTYPES]}, "read", 1, update_modified=False)`. **Not** Frappe's `mark_all_as_read` (which filters `for_user` only) and **not** a loop. Verified in Frappe's source that this shape is a single `UPDATE` through the query builder. Three separate assertions, each failing on one removed term |
| **SEC-3** | `notices.py` | The function takes **no arguments at all**; `NOTICE_DOCTYPES` is a module constant. Whitelist count: **+1 in `notices.py`, −1 in `grooming.py` = net 0**, which is inside the "+1 at most" ceiling. The crafted-keyword test calls it with `document_type=`, `for_user=`, `filters=` and `ignore_permissions=` and asserts no row outside the caller's three types moves |
| **SEC-4** | `notices.py` + CI | `ignore_permissions` stays **0**; the existing ceiling test already carries `("alvoraa_portal", "notices.py"): 0`. No raw SQL. No new file needs a ceiling row, because the code lands in a file that already has one |
| **SEC-5** | a new test on a **fresh** site | The six-door list as a plain staff login — list with no filter and with a hostile `for_user`; `reportview.get`; `reportview.get_count` with and without `reference_doctype`; `export_query` naming `subject` and `email_content`; `client.get` of a colleague's row; `has_permission(..., "share", doc=<colleague's row>)`. **The colleague's seeded row is asserted to exist first**, or the test passes on an empty table — which is exactly where PPJ and DTC are today |
| **SEC-6** | no code at all | A **hash route** inside `/hrms-employee`, so no new address, no nginx rule, no guest route. `deploy/nginx.conf` is asserted unchanged by `git diff --stat`. The `Cache-Control: no-store,...` header becomes a CI assertion, and a source assertion keeps the portal service worker a no-op (no `caches`, no `respondWith`, no `Cache`) |
| **SEC-7** | `portal.js` — by **not** writing | (a) Nothing from either feed touches `localStorage`, `sessionStorage`, IndexedDB or the Cache API; the page state lives in one module variable that dies with the page. A test asserts the set of storage call sites **has not grown** and that `sb-pinned` plus the theme key are still the only keys. (b) Back after `/logout` is a **manual check on one real Android handset, recorded with the Chrome version — a release gate (R5)**. The one-line `pagehide` fallback is named and deliberately **not built** |

### Privacy (01c §9)

| ID | Where it is met | The mechanism |
|---|---|---|
| **PRIV-1** | `notices.py` | The return's key set stays exactly `unread`, `any`, `can_send`, `items` **plus `capped`**, and the item keys are untouched. The existing fixed-key test is **extended** to include `capped`. `ROW_KEYS` is not edited. The diff contains no DocType `.json` and no Custom Field fixture — asserted |
| **PRIV-2** | nothing drawn that is not already drawn | `explanation` is not in `ROW_KEYS` and reaches no row (`reason` is the fixed-option category, verified). A name-list assertion proves no `ROW_KEYS` list holds a salary, bank, passport or health field. The leaver test covers a `Left` login that still holds HR Manager, for whom `hr_scope` returns `set()` |
| **PRIV-3** | `portal.js` | The route is the fixed word `#notifications` — no employee id, no document name, no email, in the URL, the hash, `document.title` or any `pushState` state. Verified that `panelFromAddress` accepts only `[a-z0-9-]{1,40}`, so nothing else can get in. A source assertion keeps the route a constant with no interpolation |
| **PRIV-4** | by refusal | The count returns a number; the write returns `{"ok": 1}`. No `for_user`, no email, no name, no row id belonging to anyone else. No read-receipt field, report or endpoint is added — grep-asserted |
| **PRIV-5** | a sentence, not a test | `Notification Log` rows are never deleted; a grooming-mark notice is a performance record under counsel's binding 18 Sep 2026 rule. **Pre-existing, accepted in writing by Surbhi on 6 Nov 2026 for this slice only.** I create no new store, so I inherit the gap without widening it |

### Operations (07 §1–§3)

| ID | How it is met | Note |
|---|---|---|
| **OPS-1** | the bell calls `get_nav_counts`, never `get_inbox` | asserted by the call name in a fetch-spy test |
| **OPS-2** | **added in the browser** | both calls fired together; no new server endpoint for the sum |
| **OPS-3** | **not met by me, and I will not pretend otherwise** | Nobody has measured `get_nav_counts` in DTC's configuration — pay rule set on, deep correction backlog. **This is R6's remaining half and it needs Surbhi's word for a read-only measurement.** ⚠ **DECISION E-6** |
| **OPS-4 · OPS-23** | hash route; `deploy/nginx.conf` untouched | `git diff --stat` assertion |
| **OPS-5** | chips filter the rows already fetched | fetch-spy asserts **zero** requests on a chip press |
| **OPS-6** | both calls fail silently; badge unchanged; no toast | the existing `ntBellBoot` behaviour, extended |
| **OPS-7** | **not adopted** — pre-existing, out of slice | recorded |
| **OPS-8** | a test that `NOTICE_DOCTYPES` and the seven inbox doctypes stay **disjoint** | fails if anyone adds to either side |
| **OPS-9** | no client-supplied filter, doctype, field or user | and the write is the one new endpoint, taking nothing from the client |
| **OPS-10 · OPS-18** | SEC-5's door list, on a fresh site, as a plain staff login | the `for_user` condition is now source-level fact; the test spends itself on export, report view and share |
| **OPS-11 · OPS-19** | **no cache of the badge**; assert the header that is already there | no new cache key is introduced anywhere |
| **OPS-13** | the two-statement split, by kind | one `COUNT` for announcements; one uncapped three-field read of unread grooming rows folded into the **same** `_readable` call. **If I let that become a second `_readable` call, the ≤ 14 ceiling breaks — that is the implementation constraint to hold** |
| **OPS-14 · OPS-27** | **no `setInterval`, no `setTimeout` loop, no polling** | source assertion. Refresh stays navigation-triggered through `hmRefreshIfStale`, which is the only reader of `HM_STALE_MS` |
| **OPS-15** | one set-based `UPDATE` | statement-count assertion: one write for 86 unread rows, not 86 |
| **OPS-16** | Fast 3G, named in the test | the pre-existing cold-load miss is accepted in writing, 6 Nov 2026, and is not this slice's debt |
| **OPS-17** | recorded, not fixed | PRIV-5 |
| **OPS-20** | **done** — `ashok.mittal336@ppjewellers.demo` works | I will review the screens in a browser as that login. PPJ has no notice or approval data, so most screens are empty; demo seeding stays a separate decision |
| **OPS-21** | no queue, worker, scheduled job or `frappe.enqueue` | source assertion |
| **OPS-22** | `@_limited(SELF_KEY, "user", limit=30)` on the write | **The trap is real and verified:** `gpSend` picks the method as `args !== undefined ? "POST" : "GET"` (`portal.js:15464`) and Frappe's limiter returns early for a method not in `methods=["POST"]` (`rate_limiter.py:133`). So the browser calls it with `{}` — an empty arguments object — and the test asserts **both** the request method is POST **and** the 31st call is refused by actually exceeding the limit. I will not copy `test_expense_evidence_081.py`'s shape, which reads the docstring |
| **OPS-24** | nothing new to back up | every row is an existing `Notification Log` row; ALV-299 stays open and is not mine |
| **OPS-25** | watch three things; add no alert, metric or dashboard | — |
| **OPS-26** | no secret, token, key or environment variable | — |
| **OPS-28** | ceiling 12 → **14**, with the reason in the commit message; **flatness line untouched**; existing front-end gates pass | the gates that will actually catch me are `check_portal_handlers.js` (a new handler out of scope), `check_undefined_js.js`, `check_portal_trays.js --static`, `check_design_system.py` (see §9, finding 2), `check_tag_balance.py` and `check_brand_spelling.py` |
| **OPS-29 · OPS-30** | release-plan items, Surbhi's gates | rollback is redeploy the previous `alvoraa-app` tag with `run_migrations: false`, then **prove the asset stamp changed by URL** |

---

## 9 · Five findings that change the spec — each needs one word from Surbhi

### ⚠ DECISION E-1 · `--on-primary` does not exist, and does not need to

The design's N3 says the badge's digits must use `--on-primary`. **I grepped every CSS
file, every template and `design_system.html`: there is no such token.** Adding one means
editing the token block that **seven pages** include, in four places (light default, dark
default, `[data-theme="light"]`, `[data-theme="dark"]`), and the tenant brand script as
well.

I do not need to. `templates/includes/brand_color.html` **clamps** the brand: in light
mode `--primary` is forced to lightness ≤ 44 %, in dark mode to ≥ 62 %, and `--primary-lt`
is set in the same breath to 95 % (light) or 16 % (dark). So `--primary` and `--primary-lt`
are **always** a dark/light pair, for every tenant seed including PPJ's pure black and any
pale yellow somebody chooses next year.

| Theme · brand | Background `--primary` | Digits `--primary-lt` | Contrast |
|---|---|---|---|
| light, Alvora default | `#5B4B8A` | `#EDEAF4` | ≈ 6.2 : 1 |
| dark, Alvora default | `#A99AD4` | `#2A2438` | ≈ 6.2 : 1 |
| light, PPJ black | `hsl(0,0%,0%)` | `hsl(0,0%,95%)` | ≈ 19 : 1 |
| dark, any seed | L ≥ 62 % | L = 16 % | high by construction |

**My recommendation: `background: var(--primary); color: var(--primary-lt)`.** Zero new
tokens, `design_system.html` untouched, and the contrast holds for brands nobody has
chosen yet. The visible result is exactly what the prototype draws. The only cost is that
`--primary-lt` is normally a background elsewhere, so I will say so in a comment.
**The alternative** — add `--on-primary` in five places across two shared files — is
available if Surbhi prefers the design's own naming.

### ⚠ DECISION E-2 · "exactly three call sites" cannot be built

AC-12 asks for one function that computes and paints the badge, called from exactly three
places. Today `ntPaintBadge(n)` is called from **four** (`portal.js:6816`, `6839`, `6877`,
`6903`), and the merged number has to move whenever **either** half changes — which is
Home's pending paint, Home's notices paint, `ntBellBoot`, "See all", opening one notice,
and the new page. Six.

**What I recommend, which keeps the rule's whole intent:** `ntPaintBadge()` takes **no
argument** and reads two stored numbers — `NT.work` and `NT.unread` — so there is exactly
**one** place in the built JavaScript that computes and writes the number, and every other
line only updates one of the two inputs. The test then asserts what actually matters:
**`#notif-badge`'s text is written in one function and nowhere else**, and the number is
never `d.total` and never `approvals_total`.

**⚠ Surbhi: may AC-12 read "one function, and no other code writes to the badge element",
with the named call sites listed in the notes, instead of "exactly three places"?**

### ⚠ DECISION E-3 · the bulk write should move, not be extended in place

The security engineer recommends extending `grooming.my_notices_seen` to cover
`Announcement` rather than writing a third function. I agree with the principle and the
mechanics get in the way: **`notices.py` imports `grooming`**, so `grooming.py` cannot
import `NOTICE_DOCTYPES` back without a circular import.

| Option | Cost | Why not |
|---|---|---|
| **1 · extend in place with the literal `"Announcement"`** | smallest diff | **duplicates the doctype list.** AC-33 and OPS-8 both require the filter to *be* `NOTICE_DOCTYPES`; two copies is exactly the drift those rules exist to stop |
| **2 · extend in place with a deferred import inside the function** | small, single-sourced | works, but leaves a function called `my_notices_seen` in the grooming module clearing announcements, and couples `grooming.py` to the rate-limit module |
| **3 · move it to `notices.py` as `mark_all_seen`, delete it from `grooming.py`** ← **recommended** | one function moved, one test line moved, one dead regex entry removed | **net zero new whitelisted endpoints**, the constant stays single-sourced, and it lands in the file whose own docstring says *"nothing else in the portal counts notices"* |

Option 3's price, stated plainly: it **deletes a whitelisted endpoint**. DevOps confirmed
and I re-grepped — `grooming.my_notices_seen` has **no live caller**; the only references
are `test_grooming_066.py:999` and the `WRITE_CALL` regex at `portal.js:15487`, where
`^mark(_|$)` already matches the new name, so that special case becomes dead
configuration and goes in the same commit.

**⚠ Surbhi: option 3?** The security engineer asked for "extend, not a third thing", and
option 3 honours that — it is the same function, in the right file, with one name on it.

### ⚠ DECISION E-4 · the desktop bell, and a test gap I cannot close

The design puts the bell in Frappe's navbar, immediately left of the avatar. The navbar is
**Frappe's** markup: `hrms-employee.html` is `{% extends "templates/web.html" %}`, and the
jsdom harness expands **only our own** `templates/includes/ess/` files. So **a bell that
exists only inside Frappe's navbar cannot be tested by the DOM tests that gate this
repository**, and if a future Frappe release changes the navbar the bell disappears
silently.

**What I recommend:** declare the bell in **our** `frame.html` — so `check_portal_handlers.js`
and the jsdom tests see it — and at boot move that one node into the navbar if the navbar
is there. One node, one id, one badge. If the navbar is absent (jsdom, or a changed
Frappe), our own CSS leaves it in the top strip and it still works. Plus one manual browser
check at 1180 px as `ashok.mittal336@ppjewellers.demo`.

**The named fallback if the move proves fragile:** drop US-1's navbar bell and let the
**sidebar nav item** carry the number — it is required anyway for the address, and it
already shows the badge. Nobody is left with no signal. I am not building that fallback
now.

### ⚠ DECISION E-5 · two CI gates constrain every line of the page

Not a question so much as a constraint Surbhi should know I am working inside, because it
will shape the page's look:

- **`check_design_system.py` counts font sizes on this page at 7, and the limit is 7.**
  I ran it. The seven are 11, 12, 13, 14, 16, 20 and 32 px. **`12px` is already there, so
  AC-52's badge size is free — but any other new pixel font size in this slice fails CI.**
  Every other size in the new page must be a `var(--fs-…)` token.
- **`loose_colours` has a limit of 0.** Every colour I write must be `var(--…)`. No hex,
  anywhere. This is what makes E-1's answer the right one rather than a convenience.

---

## 10 · The strategy

### 10.1 What gets built, file by file, and the rung for each

| # | File | Change | Rung | Why not cheaper |
|---|---|---|---|---|
| 1 | `notices.py` | `unread` becomes the true count; `capped` added; `mark_all_seen` moved in with the rate-limit decorator | **4** for the count (two statements of new code), **1–2** for the write (an existing function, moved) | there is no configuration that makes a capped count true |
| 2 | `grooming.py` | `my_notices_seen` removed | **—** (a deletion) | leaving it is dead code in the wrong module |
| 3 | `templates/includes/ess/parts/notifications.html` | **new part**: the panel shell — title, sub-line, three chips, three group containers, a skeleton | **4** | no Frappe or ERPNext screen gives an ESS employee this page; Frappe's own list is Desk-only |
| 4 | `templates/includes/ess/frame.html` | the desktop bell block; one sidebar nav item, a real `<button>`, second after Home | **4** | without a **visible** nav item `mayOpenPanel` cannot resolve the address and the page is lost on reload — verified at `portal.js:4707` |
| 5 | `public/js/ess/portal.js` | one new `nf` block (the page, chips, groups, states, the mark-all call); named edits in the `hm`/`nt` block: `ntPaintBadge()` loses its argument, `ntWorkOwed(d)` is added, `hmPaintPending` splits its rows and changes its chip, `ntBellBoot` fires both calls, the bell's destination becomes the page | **4** | — |
| 6 | `public/css/ess/panels.css` · `frame.css` | an `nf-` block; `.notif-badge` gains 12 px, `--primary` / `--primary-lt`, moves outside the glyph, gains a ring; the desktop bell's own rules | **4**, and **configuration** for the badge (one existing rule) | — |
| 7 | `www/hrms-employee.html` | one `{{ ess_part("notifications") }}` line | **4** | `switchPanel` does an unguarded `getElementById("panel-notifications")`; the part must be registered or `portal_source.py` calls it stranded |

**Nothing else.** No `patches.txt` entry, no `hooks.py` entry, no DocType JSON, no fixture,
no `deploy/` file, no `.github/` file.

### 10.2 The order I would build it, so each step is provable

1. **Server first, because it is the dangerous part.** The true count and `capped` in
   `notices.py`, with `test_notices_076`'s ceiling raised to 14 and the fixed-key test
   extended. Prove `small.n == big.n` still holds.
2. **The bulk write moved**, with its rate limit, and the three separate assertions —
   **each proved to fail with its own term removed, before the commit**.
3. **The badge's single writer**: `ntWorkOwed`, `ntPaintBadge()` with no argument,
   `ntBellBoot` firing both calls. At this point the bell is correct on every screen and
   nothing new is drawn.
4. **Home's chip and card**, with the missing `my_requests > 0` fixture, so Home and the
   bell are proved equal before the page exists to disagree with them.
5. **The desktop bell and the sidebar item**, then reload and Back on `#notifications`.
6. **The page**: skeleton, three groups, three chips, the five-row footers, the capped
   lines, the empty states, the two failure boxes, the stale-row sentences.
7. **Deciding from the page** — reuse `hmLeaveSheet` / `hmExpenseSheet` unchanged. **If the
   reuse is not clean, US-10 drops to later rather than growing a second sheet** (the
   spec's own instruction, and I will take it).
8. **Hindi**, the four theme × brand combinations, 200 % text, 390 px.
9. The whole suite, the front-end gates, and a browser pass as Ashok Mittal.

### 10.3 The two server changes, precisely

**The count** (OPS-13's shape, and the only shape that satisfies AC-26):

- one `frappe.db.count("Notification Log", {"for_user": <session user>, "document_type": "Announcement", "read": 0})` — exact, no gate needed, and **the explicit `for_user` is the only protection there is**;
- one uncapped `frappe.get_list` of unread grooming rows, three fields only (`name`, `document_type`, `document_name`), **folded into the single `_readable` call the function already makes** — so the gate costs **zero** extra queries;
- `unread` = announcements + the readable part of the grooming rows; `capped` = the page's own read hit `READ_CAP`.

**+2 statements, both flat.** The thing to get wrong is calling `_readable` twice; the test
that catches it is the ≤ 14 ceiling.

**The write:** one set-based `UPDATE`, `update_modified=False`, POST, limit 30/user/hour,
no arguments, returning `{"ok": 1}`. Verified in Frappe's source that a dict filter
produces exactly one `UPDATE` through the query builder — and that it clears the document
cache for the whole doctype, which is cheap and worth knowing.

### 10.4 Three things I will deliberately **not** do

- **Not** touch `inbox_api.py`. It is a hot file, it holds the one `ignore_permissions`
  with no CI ceiling (R4), and this slice needs nothing from it but two existing reads.
- **Not** fix the five stale sidebar badges, the per-row `_dtc_row_facts` N+1, `_my_employee`
  being asked twice, or `inbox_api` never opening `call_cache`. All real, all recorded, all
  someone else's slice. I will write them down again in the notes.
- **Not** add the `pagehide` row-clear. It is the right fix **if** the Android check fails,
  and writing a control before knowing it is needed is what the rule forbids.

### 10.5 The main trade-off, stated plainly

**We are paying 21 extra database statements and 638 bytes on every non-Home page load so
that a manager on a laptop does not have to go Home to find out that something is waiting.**
That is the whole bargain. It is a real cost at 483 DTC logins, it is small against a page
that is already 235 KB, and it is bounded only because there is no timer — the moment
anyone adds a 60-second refresh it becomes about 15 calls a second all day. That is why
AC-64 is a source assertion and not a comment.

**The second trade-off, and the one that will be felt:** Home's "Pending for you" number
gets smaller for anyone with an open request of their own. They lose a number they may have
been using and gain one that means something. Surbhi chose this at the brief gate; I am
restating it because it is the only visible regression in the slice.

### 10.6 The pin tests, so a bad merge cannot drop any of this

| Feature | The test that names it |
|---|---|
| the true uncapped count | `test_notices_076` — 150 unread returns `unread = 150`, `items` 100. **Fails against today's code** |
| the readability gate still applies to the count | the existing hidden-notice test, unchanged, still 1 → 0 |
| the write touches nothing else | three separate assertions: own notices read · own `Employee` rows **still unread** · colleague's rows **still unread** |
| the write is one statement and a POST, and the limit bites | statement count; request method; the 31st call refused by exceeding the limit |
| Home and the bell agree | one test painting both from one payload, **with `my_requests` greater than zero** |
| the badge has one writer, and is never `d.total` or `approvals_total` | source assertion over the built JS |
| the two doctype sets stay disjoint | a test that fails if either side grows |
| no timer, no queue, no nginx edit, no new address | source and `git diff --stat` assertions |
| the page keeps its address on reload | `mayOpenPanel("notifications")` is true because a visible nav item exists |
| the door list stays closed | six assertions on a fresh site, as a plain staff login, **after asserting the colleague's row exists** |
| nothing reaches the handset | storage call sites have not grown; `no-store` header; service worker is a no-op |

### 10.7 Subtract pass on this strategy

Read again asking only what I could delete. **Removed:**

- **The `--on-primary` token** and the edit to `design_system.html` and `brand_color.html`
  that came with it — two shared files, five places, replaced by an existing token pair
  (E-1).
- **A new `nf_api.py` module** for the count and the write. They belong in `notices.py`,
  which already owns the answer; a second file would give the doctype list two homes.
- **A second bell element** in the markup for the desktop. One node, moved, has one id and
  one badge (E-4).
- **A `resize` listener** to re-home the bell between widths. CSS handles both homes; a
  listener would be a moving part for a layout question.
- **A `NT_STALE_MS` and a refresh on returning to the page.** `hmRefreshIfStale` already
  does exactly this for Home and the page is reached through `switchPanel`, which already
  calls it for Home only — extending it to the new panel is one line if it is ever wanted,
  and nobody asked.
- **A per-chip count** and a fourth "Read" chip. Both refused upstream; neither traces to
  the brief.
- **A `COUNT_CAP`** on the grooming read. The gate adds no queries and the Python cost at
  5,000 rows is an estimated 10 ms. A cap would be a number invented to protect against
  nothing.
- **An audit field on the bulk write.** It is a new field for a behaviour nobody needs to
  reconstruct; §14 of the spec says so in a sentence instead.

**Kept despite the pass, each with a reason:** the three separate write assertions, because
a wrong write here is silent and unlogged and one combined assertion would not name the
cause; the sidebar nav item, because without it the page has no address; and the
`my_requests > 0` fixture, because without it the one test that proves Home and the bell
agree passes on a coincidence.

---

## 11 · What I verified myself, and what I did not

**Verified by reading the code in this worktree at `814d540f`, and Frappe 16.33.1 inside
the running container:**

- `frappe.__version__ = "16.33.1"`.
- `frappe.db.set_value` with a **dict** filter builds one `UPDATE` through the query
  builder and clears the document cache for the whole doctype (`database.py:934–1001`).
- `frappe.db.count` is a plain `COUNT(*)` through the query builder with **no permission
  condition** (`database.py:1285`).
- `gpSend` sends a no-argument call as a **GET** (`portal.js:15464`), and `WRITE_CALL`'s
  `^mark(_|$)` already covers a `mark_all_*` name (`:15487`).
- `_limited(SELF_KEY, "user", limit=N)` exists, is keyed on the hashed signed-in user, with
  a 3600 s window, `ip_based=False`, `methods=["POST"]`, and refuses through `frappe.throw`
  so the sentence reaches the screen (`field_app_limits.py:56–91`).
- `mayOpenPanel` resolves a panel only through a **visible** `.nav-item[data-panel=…]`
  (`portal.js:4707`); `applyPlanNav` touches only named ids, so an ungated new item stays
  visible; `panelFromAddress` accepts only `[a-z0-9-]{1,40}`.
- `switchPanel` does an **unguarded** `getElementById("panel-" + name)`, so the panel markup
  must exist.
- `get_nav_counts` and `get_inbox` return the **same** `parts[{key, count}]` shape
  (`inbox_api.py:1138`, `:1181`); `APPROVAL_PARTS` includes `shift_requests` (`:88`);
  `total = approvals + policies + my_requests` (`:1132`).
- `.notif-badge` is `--red` on `--surface` at `--fs-xs`, 16 × 16, inside the glyph
  (`panels.css:1482`); `.mob-header` is `display:none` except below 768 px
  (`frame.css:231`, `panels.css:367`).
- `--on-primary` **does not exist**; `brand_color.html` clamps `--primary` and sets
  `--primary-lt` in step.
- `design_system.html` is included by **seven** pages.
- `check_design_system.py` reports **7 font sizes against a limit of 7** on this page, and
  `12px` is already one of them. `loose_colours` limit is 0.
- `my_notices_seen` has **no live caller**; `test_grooming_066.py:999` and the `WRITE_CALL`
  regex are its only references.
- `portal_home_076_test.js:248` asserts the bell's name is exactly `"Notices, 3 unread"`,
  and every pending-chip fixture in that file has `my_requests` count 0.
- `hrms-employee.html` is `{% extends "templates/web.html" %}`, so Frappe's navbar is not
  in the jsdom fixture.

**Not verified, and I will not pretend otherwise:**

1. **Any timing, anywhere.** I measured nothing. Every millisecond in §7 is slice 044's
   September 2026 measurement on fixture sites, or an estimate.
2. **`get_nav_counts` in DTC's configuration** — pay rule set on, a deep correction
   backlog. OPS-3 / R6's remaining half. ⚠ **DECISION E-6: may I measure it read-only?**
3. **Chrome Android's back/forward cache** after sign-out. R5, a release gate, one handset.
4. **Any screen.** I have not opened the portal in a browser in this run. I will, as
   `ashok.mittal336@ppjewellers.demo`, before I report the build — knowing PPJ has no notice
   or approval data, so most of what I can see is the empty states.
5. **Whether the other session's uncommitted `frame.css` / `panels.css` edits overlap mine.**
   They are in the shared checkout and not mine to read into my work. I will check before
   any bench run and tell Surbhi.

**What I changed anywhere: nothing.** No bench command, no site opened, no record edited,
no cache cleared, no container started or stopped, nothing against dev or production, and
not one file in the shared checkout.

---

## 12 · What I need from Surbhi before I write a line

| # | Decision | What it changes | My recommendation |
|---|---|---|---|
| **E-1** | The badge's digits: `var(--primary-lt)`, or add a new `--on-primary` token to `design_system.html` and `brand_color.html`? | one CSS line, or five lines across two files seven pages share | **`--primary-lt`.** Identical on screen, passes 4.5 : 1 in all four combinations and for brands nobody has chosen yet, and touches nothing shared |
| **E-2** | May AC-12 read "one function, and no other code writes to the badge element" instead of "exactly three call sites"? | the wording of one AC and the shape of one function | **Yes.** Three is not buildable; one computing place is, and is what the rule is for |
| **E-3** | Move `my_notices_seen` to `notices.py` as `mark_all_seen` and delete it from `grooming.py` — removing a whitelisted endpoint with no live caller? | one function, one test line, one dead regex entry | **Yes, option 3.** Net zero new endpoints and the doctype list stays single-sourced |
| **E-4** | The desktop bell declared in our `frame.html` and moved into Frappe's navbar at boot, with our CSS position as the fallback? | three lines of JavaScript and one CSS block | **Yes.** It is the only shape that is both faithful to the design and visible to CI |
| **E-5** | Noted, not a question: every new font size must be an existing token or one of 11/12/13/14/16/20 px, and every colour a `var()` | the page's look, slightly | — |
| **E-6** | May I measure `get_nav_counts` and `notices_feed` **read-only** on a DTC-shaped copy before part 3 ships? OPS-3 / R6's open half | nothing in the build; it is the one number this slice does not have | **Yes, read-only.** Without it we ship the one call that is now on every page having never measured it where it runs |
| **E-7** | Confirm the analyst's **BA-1**: drop brief §12 success measure 1 ("share of approvals decided from the notifications page"), because measuring it needs a new field | one success measure, nothing in the build | **Drop it**, on the brief's own instruction |

**Still open from the spec and not mine to close:** AC-51's named Hindi reader (a release
gate), AC-63's Android handset check (a release gate), and demo seeding so this page can be
seen with data on the bench.

---

**Written by `hrms-fullstack-engineer`, 11 November 2026. No code written, nothing
committed, nothing deployed. I recommend; Surbhi decides.**
