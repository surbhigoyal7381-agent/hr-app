---
slice: 083-ess-notifications
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-11-12
status: built locally. Nothing pushed, nothing on dev, nothing deployed.
        **Two things could not be run and I am not pretending otherwise** — the
        Python suite and the browser review. Both have the same cause and it is
        not the code. See section 6.
inputs: [00-impact-analysis.md, 02-functional-spec.md, 01b-ux-design.md,
         01c-security-privacy-requirements.md, 07-devops-inputs.md (all four parts),
         08-dtc-counts.md, prototype-v1.html, .claude/context/parallel-work.md,
         no-over-engineering.md, data-doors.md, nfr-budget.md]
ticket: ALV-322 (Epic)
worktree: .claude/worktrees/083-ess-notifications · slice/083-ess-notifications
          · rebased onto origin/dev dd609e0d
---

# 083 · Implementation notes

## Answer first

**Built, and every gate I can run on this machine is green.** The three parts are
in: the bell on a laptop, a notifications page at `#notifications`, and a badge
that counts work owed as well as unread notices. 169 browser assertions pass (80
new, 89 in slice 076's own Home test, which I changed in two places and say so
below), and all eight static gates exit 0.

**Two things I could not run, and the reason is the same for both: Docker is not
running on this machine, and the shared checkout is not in a state I am allowed
to fix.**

1. **The Python suite did not run.** `bench run-tests` needs the bench, the bench
   mounts the shared checkout `C:/Surbhi-Git/hr-app`, and that checkout still
   holds another session's uncommitted edits to the two CSS files I touch — plus
   287 other modified files, and a local `dev` at `5aa654d2`, which is *behind*
   `origin/dev`. A `merge --ff-only` into it would be refused, and the five
   commands that would force it through are the ones that destroy another
   session's work. **A refusal is the safe outcome, so I stopped.** On top of
   that, `docker ps` cannot reach the engine at all right now, so no bench exists
   to run against even if the checkout were clean. **I wrote 23 new Python
   assertions and have not seen one of them execute.** Section 6 says exactly
   what that leaves unverified.
2. **No browser review.** Same two reasons — no running bench, no site. The
   demo login `ashok.mittal336@ppjewellers.demo` was never reached.

**Nothing else is outstanding.** No file outside the plan, no new dependency, no
`deploy/`, `.github/`, `hooks.py`, `patches.txt` or DocType JSON in the diff, no
`ignore_permissions`, no raw SQL, no timer, no cache, no job, no new web address.
Net whitelisted endpoints: **zero** (one added, one deleted).

**One file the plan did not predict**, and it would have been a red CI: a new
`position:fixed` element needs an entry in `scripts/check_portal_trays.js`'s
`INVENTORY`. DevOps found the `check_tag_balance.py` gap; this is the same shape
and neither of us had it. Both are in.

---

## 1 · What I built, file by file

Rung on the cost ladder is in the last column: **1** already there, **2**
configuration, **3** customisation, **4** new code.

| # | File | What changed | Rung | Why not cheaper |
|---|---|---|---|---|
| 1 | `alvoraa_portal/notices.py` | `unread` became the true uncapped count; `capped` added; `mark_all_seen` moved in with the rate-limit decorator | **4** for the count, **1–2** for the write | No configuration makes a capped count true. The write already existed — it moved, it was not written |
| 2 | `alvoraa_portal/grooming.py` | `my_notices_seen` **deleted** (11 lines) | — | Leaving it is a whitelisted endpoint, with no caller, clearing two of the three notice kinds from the wrong module |
| 3 | `templates/includes/ess/parts/notifications.html` | **new part**: the panel shell — title, sub-line, chip row, body. 29 lines, **no Jinja at all** | **4** | No Frappe or ERPNext screen gives an ESS employee this page, and Frappe's own Notification Log list is a Desk screen ESS staff cannot reach |
| 4 | `templates/includes/ess/frame.html` | the desktop bell (declared here, moved at boot); one sidebar nav item, a real `<button>`, second after Home; the phone bell's name and comment | **4** | Without a **visible** nav item `mayOpenPanel` cannot resolve the address and the page is lost on reload |
| 5 | `public/js/ess/portal.js` | one new `nf` block (the page, ~290 lines) plus named edits in the `hm`/`nt` block: `ntWorkOwed`, `ntPaintBadge()` with no argument, `hmOwnRows`, `hmOwnHead`, `hmPaintPending`'s number and split, `hmPendAll`, `hmPendOpen`, `ntBellBoot`'s two calls, `ntOpenOne`, `hmDropPending`, `hmDecide`'s refusal path, three click targets, `switchPanel`, the bell's destination, `nfHomeTheBell`. The dead `my_notices_seen` entry removed from `WRITE_CALL` | **4** | — |
| 6 | `public/css/ess/panels.css` | the `.notif-badge` rule rewritten (12 px, `--primary` on `--primary-lt`, 18 px, outside the glyph, a ring); `.nav-badge.nf-count`; an `nf-` block for the page; `.hm-subh` for Home's sub-heading | **4**, and **2** for the badge (one existing rule) | — |
| 7 | `public/css/ess/frame.css` | the desktop bell's own rules, hidden below 768 px | **4** | — |
| 8 | `www/hrms-employee.html` | one `{{ ess_part("notifications") }}` line | **4** | `switchPanel` does an unguarded `getElementById("panel-" + name)`; without the part every route to `#notifications` throws |
| 9 | `scripts/check_tag_balance.py` | `PINNED_DEPTH["notifications.html"] = 0` | **2** | DevOps OPS-33. Without it CI fails with *"parts/notifications is new and has no pinned depth"* |
| 10 | `scripts/check_portal_trays.js` | `INVENTORY[".nf-bell"]` | **2** | **Not in anybody's plan.** See section 7 |
| 11 | `scripts/run_dom_tests.js` | the new test registered; `EXPECTED_BROWSER_TESTS` 23 → 24 | **2** | The runner fails rather than silently running less |
| 12 | `tests/test_notices_076.py` | ceiling 12 → **14**; the key set gains `capped`; **23 new assertions** in two new classes | **4** | — |
| 13 | `tests/test_inbox_parts_042.py` | the **backlog-depth** assertion on `get_nav_counts` (DevOps OPS-40) | **4** | — |
| 14 | `tests/test_grooming_066.py` | the one call to the moved function | — | — |
| 15 | `tests/portal_home_076_test.js` | two assertions changed deliberately; the missing `my_requests > 0` fixture; 11 new assertions | — | See section 3 |
| 16 | `tests/portal_notifications_083_test.js` | **new**, 80 assertions | **4** | — |

**Three choices worth naming, because each one removed work the plan expected:**

- **Home's sub-heading is drawn in JavaScript, not in `parts/home.html`.** The
  impact analysis planned a markup change there. `hmPaintPending` already writes
  that card's whole body through `innerHTML`, so the sub-heading is a string in
  the same function — one file fewer, and no new id in shared markup.
- **The page's work rows reuse Home's own `data-hm="pend"` handler, unchanged.**
  Both surfaces read the same `get_inbox` payload held in the same `HM` state,
  so `HM.rows` is the same array on both. The page needed **three** new click
  targets (`nf-chip`, `nf-mark`, `nf-retry`), not eight, and a decision taken on
  the page moves Home's card because it is literally the same code.
- **The skeleton reuses `.hm-skel`**, the product's own pulse bar, resized by one
  rule. No new animation and no second `prefers-reduced-motion` exemption.

---

## 2 · The acceptance criteria, and how each is satisfied

**Proved by an automated assertion: 54.** **Satisfied in code but not yet
executed (Python, section 6): 13.** **Manual release gates, by design: 3.**
**Changed with a reason: 2.** **Not satisfied: 1.**

### US-1 · the bell on desktop

| AC | How | Proof |
|---|---|---|
| AC-1 | `.nf-bell` declared in `frame.html`, 36 × 36, moved into the navbar left of the avatar by `nfHomeTheBell`; name `"Notifications, {N} waiting"` from `ntPaintBadge` | jsdom: the button exists, is not inside `.mob-header`, and carries the name. **The 1180 px placement itself is unverified — no browser** |
| AC-2 | `.notif-badge` is 18 × 18 at `top:-4px;right:-4px` with a 2 px `--surface` ring; `99+` above 99 | jsdom asserts `99+` and the shared class |
| AC-3 | `display:none` at zero; the name still carries 0 | the existing 076 assertions, plus the empty-state cases |

### US-2 · the sidebar item

AC-4, AC-5, AC-6 — all three asserted in jsdom: the item exists, is **visible**,
`mayOpenPanel("notifications")` is true, it is a `<button>`, it carries the word,
and it is **index 1** in the rail (second, after Home).

### US-3 · the page

AC-7, AC-8, AC-9, AC-10 — asserted: the title and sub-line, three groups in the
fixed order with the right headings and tags, oldest-`waiting_since`-first across
kinds, and group 3's rows are `DIV`s with no button inside them.

### US-6 · the number

| AC | How | Proof |
|---|---|---|
| AC-11 | `ntWorkOwed` sums `parts[].count` skipping `shift_requests` and `my_requests`; `+ NT.unread` | asserted twice — the badge is **7** on the spec's own payload, and is neither of the wrong answers |
| **AC-12** | **changed wording, Surbhi's E-2 decision.** `ntPaintBadge()` takes no argument and reads two stored halves | **exactly one line in the whole 24,575-line file names the badge elements**, and nothing passes the function a number. Both asserted by grepping the built source |
| AC-19 | the page's two counted headings reconcile the badge | asserted: heading 1's number + heading 2's number equals the badge |
| AC-20 | the doctype sets are disjoint | Python, with a tripwire if either side grows |

### US-7 · Home agrees with the bell

AC-21 (chip reads "4 waiting"), AC-22 (own requests under their own sub-heading,
in DOM order, with no approval row below it), AC-23 (one payload, both surfaces,
one number) — all asserted, **on the `my_requests > 0` fixture this file never
had**. Plus the footer fix, asserted: "Showing 5 of 6" above "See all 6".

### US-8 · the true count

AC-24 (150 → `unread` 150, `items` 100), AC-25 (`capped` and the words on
screen), AC-26 (the `_readable` gate still applies to the count), AC-27 (ceiling
14, flatness untouched) — **written, not executed.** AC-25's on-screen half and
AC-18's footer total **are** proved in jsdom against a 150/100 payload.

### US-9 · mark all as read

| AC | How | Proof |
|---|---|---|
| AC-28 | the control is in the notices group head only, and **absent** when nothing is unread | jsdom, both states |
| AC-29 | nothing can mark a work row | jsdom: exactly one `nf-mark` on the page and its `.nf-grp` **is** group 2 |
| AC-30 / 31 / 32 | one `set_value` with `for_user` **and** `document_type in NOTICE_DOCTYPES` | three separate Python assertions, each failing on its own removed term. **Written, not executed** |
| AC-33 | one set-based `UPDATE` | Python statement count ≤ 2 for 86 unread rows |
| AC-34 | `@_limited(SELF_KEY, "user", limit=30)` | **the POST half is proved in jsdom** — the request method is asserted `POST` and the body `{}`. The numbers are pinned in Python off `__alvoraa_limit__`. **The refusal by exceeding the limit is NOT written: it needs a real request, and I could not run Python at all.** Named as a gap |

### US-10, US-11, US-12, US-13, US-14, US-4, US-5

- AC-35 asserted (the existing leave sheet opens in place). AC-36 asserted (any
  other row navigates and sends nothing).
- AC-37, AC-38 asserted word for word, including **no toast** and **the bell's
  number unchanged**. AC-39 (`PermissionError` inside one part) is
  `inbox_api`'s own behaviour, untouched; **not asserted by me.**
- AC-40 asserted (four named `aria-busy` bars, replaced by rows, a box or an
  amber box). AC-41, AC-42, AC-43, AC-44 asserted word for word.
- **AC-45, AC-46 — changed, see section 3.** AC-47 satisfied by saying nothing.
- AC-48, AC-49 asserted (the CXO badge is 4, not 279; no colleague named).
  AC-49a follows from AC-36's path; not separately asserted.
- AC-13, AC-14, AC-15 asserted — including **zero network calls on a chip press**.
- AC-16, AC-17, AC-18, AC-18a asserted.

### US-15, US-16 · Hindi and legibility

- AC-50: every new string goes through `drT()` — including the page title and
  the sub-line, which is why the part file carries no text at all. **The Hindi
  rendering itself is not verified: no browser.**
- AC-51: a named native Hindi reader. **Release gate, open.**
- AC-52: 12 px set in `.notif-badge`'s own rule. `design_system.html` is
  **not in the diff**.
- AC-53: `--primary` on **`--primary-lt`** (Surbhi's E-1 decision), never red.
- AC-54: **not verified.** The contrast argument is the clamp in
  `brand_color.html`, read, not rendered. DevOps asked for a tenant with **no**
  brand seed to be included; that needs a browser.
- AC-54a: a dot **and** the group, a number **and** a spoken name — the dot is
  the existing row markup, the name is asserted.

### US-17, US-18, US-19, US-20, US-21 · the "must nots"

| AC | Status |
|---|---|
| AC-55 (the six doors on a fresh site) | **not written.** It is a Python test needing a fresh site and a plain staff login. Routed to `hrms-test-automation-engineer`; named as a gap, not quietly skipped |
| AC-56 | written (own count, and strictly less than site-wide). Not executed |
| AC-56a | written — `inspect.signature` is empty, and a crafted call changes nothing |
| AC-56b | the existing ceiling test already carries `notices.py: 0`; the whitelist count is **net zero**. Not re-run |
| AC-56c, AC-56d, AC-56e | the leaver case is covered by the existing hidden-notice test; the key set is asserted **exactly**, now including `capped`; the write returns `{"ok": 1}` and the count a number. No DocType JSON and no Custom Field in the diff — checked |
| AC-57, AC-58 | **asserted in jsdom** — a fetch count across a tap, and no dismiss/snooze/mark-done control |
| AC-59 | **asserted** — the block's own code (comments stripped) names no storage API |
| AC-60, AC-61, AC-62 | pre-existing behaviour, **not asserted by me.** Named as a gap |
| AC-63, AC-63a | the route is a fixed word (asserted). **The Android Back check is a release gate, open** |
| AC-64, AC-65 | **asserted** — no `setInterval`, no polling, no `frappe.enqueue` |
| AC-66 | `deploy/nginx.conf` is not in the diff; no new address. Checked by `git diff --name-only` |
| AC-67 | the flatness line is untouched, the ceiling reads 14, and **every front-end gate exits 0** (section 5). `test_scale_flatness_044.py` and `test_inbox_parts_042.py` needed no change — I **added** to the latter rather than changing it |

### The one AC I did not satisfy

**AC-39.** One part of `get_nav_counts` raising `PermissionError` must leave the
bell as it was. The behaviour is right — `ntBellBoot`'s handler for that call
does nothing at all on failure, and `inbox_api`'s own ALV-250 fix is untouched —
but I wrote no test that makes one part raise. It belongs with the Python work I
could not run.

---

## 3 · Where I departed from the spec or the prototype

Every difference, per the prototype-parity rule. **Three need Surbhi's word.**

| # | What the spec or prototype says | What I built | Why | Needs Surbhi? |
|---|---|---|---|---|
| D-1 | **AC-12**: "one function … called from exactly three places" | one function, **no argument**, and no other code writes the badge element | Decision **E-2**, accepted 12 Nov. The merged number has to move wherever either half changes, which is six places; the rule's intent is one computing place, and that is what is asserted | **recorded, already decided** |
| D-2 | **AC-45 / AC-46**: the page shows "Already decided by someone else." / "The request was withdrawn." | the **server's own sentence** is shown — "Anita cancelled this request.", "This claim has already been decided." — and the page then re-asks both feeds, so a row that really left the queue disappears | The spec's own §11.2 says these refusals "are the server's own sentences… The spec does not rewrite them", and §11.1's versions are the prototype's. Matching them would mean string-matching the server's message to decide which of our two sentences to show — and getting it wrong on a refusal like "No leave approver is set for Rakesh", where the row is still owed and must **stay**. Re-asking is right in every case | **⚠ yes** |
| D-3 | **AC-44**: "an employee whose record was created today" | "nothing at all **and** `notices_feed.any` is false" — i.e. they have never had a notice in the window | There is no joining-date field on either payload and the brief's rule is drop rather than add one. `any` exists for exactly this distinction — its own docstring says so | **⚠ yes, on the reading** |
| D-4 | §11.1: "Showing the first {0} of {1} attendance fixes" | "Showing the first {0} of {1} {2}", with the kind as a third placeholder | `get_inbox` can cap **any** part, not only attendance fixes. One translatable sentence covering five kinds instead of five near-identical ones. §11.1's Hindi draft needs re-wording to match | **⚠ yes, one string** |
| D-5 | design/prototype: the notices footer total is the group's own row count | `unread` when the unread backlog is larger than the five shown, otherwise the row count | AC-16's worked example (86 unread of 100 rows → "See all 86 notices") and AC-18 (150 unread → 150) both want the unread count; the prototype's code uses `list.length`, which would say 100 and 100. The two cannot both be honoured, so I followed the two ACs. The visible difference is a small case the design does not draw: 10 rows of which 8 unread now reads "of 8" where the prototype would say "of 10" | no — the spec is the stricter answer |
| D-6 | prototype: a work-call-only failure is not drawn | the **AC-38 box** inside group 1 | The spec specifies only the notices-failed-alone case. Writing a mirrored sentence pair would be two strings of invented copy and two Hindi drafts nobody has reviewed, so I used copy that already exists and is true of the group that failed | no, but it is not pretty |
| D-7 | §10.1 of the impact analysis: Home's sub-heading goes in `parts/home.html` | it is a string in `hmPaintPending` | That function already writes the card's whole body. One file fewer | no |
| D-8 | an own-request row on **Home** | still a button, navigating to its own screen, as it does today | AC-10 makes group 3 static **on the page**, and it is. Nothing asked for Home's existing behaviour to be removed, and taking it away would be a regression nobody requested | no |
| D-9 | a read-notice backlog under "All" | reachable only as the first five, when there is no unread backlog | The third chip is unread-only by the approved design (UX-2 refused a fourth "Notices" chip), so there is no destination for "see all read notices" in this slice. 30 days of read notices beyond the first five are not reachable from this page | no — traceable to UX-2, but say it out loud |

**Slice 076's own pin test, changed deliberately in two places** — flagged loudly
because `parallel-work.md` §7 exists to stop exactly this being done quietly:

1. `portal_home_076_test.js:248` asserted the bell's accessible name is exactly
   `"Notices, 3 unread"`. It now asserts `"Notifications, 3 waiting"`, with a
   seven-line comment naming design `01b` §6.1 as the decision that replaced it.
   **The assertion's intent is not weakened** — it still proves the name carries
   the number, and a second assertion now proves the number is work **plus**
   notices.
2. "the bell opens the Notices sheet" became "Home's See all opens the Notices
   sheet", plus a new assertion that **the bell opens the page**. Only the bell's
   destination changed; Home's own "See all" still opens the sheet it always did.

---

## 4 · The seven non-functional dimensions, re-assessed against the code I wrote

Not the proposal. These are read off the diff.

| Dimension | Before | After | Verdict | The argument, with what changed from the proposal |
|---|---|---|---|---|
| **Performance** | `get_nav_counts` had no caller; `notices_feed` ≤ 12 statements | **+2 statements on `notices_feed` and one `get_nav_counts` (≈21 statements, 638 B) on every non-Home page load** | **degrades, as accepted** | Unchanged from the proposal except in one direction: `ntBellBoot` now skips each half that Home has **already asked for**, keyed on a flag set when the request goes out rather than when it lands. Before this slice a slow Home could be asked for notices twice; it cannot now. The page's own open costs two calls, and I chose always to re-ask rather than reuse a cached payload — one paint path, and the AC-40 skeleton is what the design draws. **No timer, asserted. No cache, no index, no job.** Nothing is on the critical render path: the bell's calls are still behind the 1,500 ms boot timer and the page's are user-initiated |
| **Security** | two unprotected tools, no tested contract | the same two tools, with the filter terms as the whole control and three assertions behind them | **improves** | As proposed, with one thing I can now state rather than predict: the write **takes no arguments at all**, proved by `inspect.signature` being empty, so there is no parameter for a crafted doctype, user or filter to arrive in. `ignore_permissions` stays at 0 — `check_scope_traps.py` and the existing ceiling both green. No raw SQL. Whitelisted endpoints: **net zero**. **The caveat is real: none of the three write assertions has been executed** |
| **Reliability** | one call behind the bell | two calls, each failing alone, neither allowed to blank anything | **improves slightly** | As proposed. Asserted: a failed notices call leaves group 1 whole, puts one amber box inside group 2, shows **no toast**, and leaves the bell's number **exactly as it was**; both failing gives one box and no half-drawn groups; "Try again" reloads only what failed. The write is safe to run twice. **One behaviour I added beyond the proposal**: a refused decision re-asks both feeds, which is what makes a stale row disappear without guessing from the server's words (D-2) |
| **Scalability** | flat in headcount | flat in headcount **and** in backlog depth, with a test for the second | **improves** | Better than proposed. The proposal left backlog depth measured by nobody; DevOps pointed out that the axis is untested and now `get_nav_counts` has a standing assertion that its statement count does not grow when the correction queue goes from 3 rows to 40. A one-off number would have decayed. The grooming count's gate adds **zero** queries whatever the row count — longer `IN` lists, not more queries |
| **Maintainability** | `ntPaintBadge` had two expressions for one number; a dead endpoint in the wrong file | one expression, one endpoint, one definition of "work owed" | **improves, narrowly** | Deletions: 11 lines of `grooming.py`, the dead `WRITE_CALL` entry, two unused window exports, a dead CSS rule, a test stub branch nothing used. Against it: `portal.js` grew by **~500 lines** and is now 24,575 — the single biggest cost in this slice, and it is contained only by the `nf` prefix and by touching nothing outside the lines named in section 1. Honest extra: the page and Home now **share `HM.rows`**, which is why three new click targets were enough but also means a future change to `hmPendingRows` moves two screens |
| **Data integrity** | a badge that could say 99+ and never clear | the count equals the list it links to, and says when the list was cut | **improves** | As proposed, and the headline fix. One risk restated rather than hidden: `update_modified=False` means **nothing records when a bulk clear happened**. Accepted in the spec §14; it is still a gap. No cache anywhere, so nothing can be stale |
| **Compliance / privacy** | — | entitlement widens by nothing; one real change in exposure shape | **neutral on entitlement** | Nothing new collected, stored, copied, logged or exported. No new field, no DocType JSON, no Custom Field — checked against the diff. The return's key set is still asserted **exactly**. Every field drawn was already in `ROW_KEYS`; `explanation` reaches no row. What genuinely changes: **30 days of one named person's HR messages become a durable, bookmarkable page two taps from any screen, on handsets 441 DTC staff share.** The controls are the session, `no-store`, **no client storage (asserted)**, a no-op service worker and a route with no identifier in it. **The last link — Chrome Android's Back after sign-out — is unproven and is a release gate** |

---

## 5 · What I ran, and what it said

Everything below was run in **this worktree**, where no bench is needed and the
other session's uncommitted CSS cannot reach it.

```
python scripts/check_design_system.py       exit 0
  hrms-employee.html  palette 6  loose 0  undef 0  sizes 7(limit 7)
                      shadows 0  radii 3(limit 3)  gradient 0  emoji 0
  -> still 7 of 7 and 3 of 3. No new pixel font size, no new hand-written
     radius, no literal colour anywhere - including in the new JavaScript,
     which this gate reads inlined.
python scripts/check_tag_balance.py         exit 0  (2 pages, 20 fragments)
python scripts/check_brand_spelling.py      exit 0  (0 visible 'Alvoraa')
python scripts/check_app_integrity.py       exit 0  (923 checks)
python scripts/check_api_paths.py --max 0   exit 0  (288 paths, 0 unresolved)
python scripts/check_scope_traps.py         exit 0
node   scripts/check_portal_handlers.js     exit 0
node   scripts/check_undefined_js.js        exit 0
node   scripts/check_portal_trays.js --static
                                            exit 0  (29 fixed elements, 29 in INVENTORY)
node   scripts/run_dom_tests.js             exit 0
  24 DOM tests, every one green. The two that matter here:
    portal_notifications_083_test.js   80 passed, 0 failed   (new)
    portal_home_076_test.js            89 passed, 0 failed   (was 78)
ruff check (notices.py, grooming.py, both test files) --config hrms/pyproject.toml
  -> 27 findings on the two source files, which is EXACTLY the baseline count
     for the same two files at dd609e0d. My code adds none. (ruff is
     non-blocking in CI and the repo carries a pre-existing backlog.)
git diff --name-only origin/dev...HEAD | grep -E 'deploy/|\.github/|patches\.txt|hooks\.py|\.json$|hrms/'
  -> no match. No deploy file, no workflow, no patch, no hooks entry, no
     DocType JSON, no upstream file.
```

**Not run, and why:**

```
bench --site test_site run-tests --app alvoraa_portal      NOT RUN
docker ps                                                  cannot reach the engine
```

**Three independent blockers, all outside the code:**

1. **Docker is not running.** `docker ps` fails at the named pipe. Starting the
   engine would also start other sessions' containers (`hrlocal-326*`,
   `hrlocal-067`, the proxies) and I was told to leave them alone.
2. **The shared checkout is not mergeable and I may not make it so.** Its `dev`
   is `5aa654d2`, behind `origin/dev` `dd609e0d`, with **289 modified files** —
   including both `frame.css` and `panels.css`, which this slice also changes. A
   `merge --ff-only` is refused, and every command that would force it through
   (`stash`, `reset --hard`, `checkout .`, `restore .`, `clean`, `add -A`,
   `add .`, `commit -a`) takes or destroys another session's unsaved work. I ran
   exactly one command against it, and it was a read:
   `git -C C:/Surbhi-Git/hr-app status --porcelain -- <the two CSS files>`.
3. The bench serves that checkout, so even a running bench would have tested
   someone else's working tree, not mine.

**What I changed outside my worktree: nothing.** No bench command, no site, no
record, no cache cleared, no container started or stopped, no `docker cp`,
nothing against dev or production, and not one byte written to
`C:/Surbhi-Git/hr-app`.

---

## 6 · What is unverified, precisely

So nobody has to guess what "the Python suite did not run" covers.

**23 new Python assertions have never executed.** They are:

| Class | Assertions | What is at risk if one is wrong |
|---|---|---|
| `TestTheTrueUnreadCount` (6 tests) | 150 unread counts as 150 · an announcement and a grooming notice are both counted · the count ignores a notice whose mark is no longer readable · the count is the caller's own and strictly less than the site's · `capped` is false for a short list · the two doctype sets are disjoint | The badge's number. A missed `_readable` fold would count notices about marks the reader may not see |
| `TestMarkAllSeen` (8 tests) | the three separate write assertions · one statement for 86 rows · safe to run twice · no arguments at all · the limit's three numbers · Guest refused | **The riskiest lines in the slice.** A wrong write is silent and unlogged |
| `TestADeepBacklogCostsNoMoreQueries` (1 test) | `get_nav_counts`' statement count does not grow from 3 rows to 40 | The call that is now on every non-Home page load |
| the two edits | the raised ceiling (12 → 14) · the key set including `capped` | Whether the two extra statements are really two |

**Three I know I did not write**, routed rather than hidden:

- **AC-55**, the six-door list on a fresh site as a plain staff login. It is the
  canary for the ALV-249 shape and it is the single most important test in the
  slice. `hrms-test-automation-engineer`'s, and it needs a fresh site.
- **AC-34's refusal by exceeding the limit.** The POST half is proved in jsdom;
  the 31st call being refused needs a real request.
- **AC-39**, one part of `get_nav_counts` raising.

**Four things nobody has seen on a screen:** the bell at 1180 px in the real
navbar, the four theme × brand contrast combinations (including a tenant with
**no** brand seed, which DevOps asked for), Hindi at 390 px, and 200 % text.

**And the one number this slice still does not have:** `get_nav_counts` measured
in DTC's configuration. DevOps's OPS-40 asked for the test first and the
measurement second; **the test is in** and the measurement is not. Per Surbhi's
E-6 decision I did not restore or copy DTC, and I did not probe production.

---

## 7 · What else moved while I worked

**`origin/dev` moved on, and I rebased onto it before writing a line.**

`HEAD..origin/dev` held **six commits**, not the one the task named — `dd609e0d`
is the head of a six-commit series:

| Commit | What came in |
|---|---|
| `37d921ec` | **ALV-318**: the joiner role can only be handed out by the invite |
| `dcd9353f` | **ALV-319**: taking the joiner role away frees the account again |
| `0afd3f45` | the tests that stop either fault coming back |
| `cce9818c`, `83d142b5`, `dd609e0d` | the analysis, the notes and the re-run (292 tests, every batch green) |

Files: `auth.py` (+62), `hooks.py` (+32), `joiner_invite.py` (+131),
`tests/test_joiner_079.py` (new, 244 lines),
`tests/test_joiner_to_employee_082.py`, `tests/test_portal_security_010.py`.

**I read the whole `hooks.py` diff before touching anything**, because it was the
one file we might have met in. ALV-318 turned `doc_events["User"]["validate"]`
from a string into a list, added a `Role Profile` validate hook and an
`after_migrate` entry. **I touch `hooks.py` nowhere**, so there was nothing to
reconcile — and nothing of theirs is at risk from this slice.

**No conflicts.** The rebase replayed one commit (the slice's own docs) cleanly.
No file this slice changes was touched by those six commits. **I proved nothing
of theirs was lost** the cheap way: `git diff origin/dev...HEAD --name-only`
lists only my 16 files, and all six of their commits are ancestors of my HEAD
(`git log --oneline origin/dev..HEAD` shows four commits, all mine).

**The work board** showed ALV-318/319 (now landed), ALV-281 and ALV-326. None
touches a file I touch.

**The two CSS files are still another session's.** Both `frame.css` and
`panels.css` were modified and uncommitted in the shared checkout when I started
and still were when I finished. My edits are appended blocks with the `nf-`
prefix plus the one existing `.notif-badge` rule, written **in my worktree**, and
I never read their lines into my work, staged them, reverted them or tidied them.
**That session has not committed, so the bench route is still shut.**

---

## 8 · NFR notes

- **Query counts.** `notices_feed`: ≤ 12 → **≤ 14**, both new statements flat in
  headcount and in row count. `get_nav_counts`: **unchanged** (21 worst case),
  and now with a standing assertion that backlog depth does not move it.
  `mark_all_seen`: **one** `UPDATE` for any number of unread rows.
- **Indexes added: none.** No measured number misses the budget, and the only
  usable index for the new reads is `for_user`, which exists.
- **Background jobs: none.** No `frappe.enqueue`, no `scheduler_events`, no
  worker, no timer — the last one asserted in the built source.
- **Caches: none added.** The page holds its state in one module variable that
  dies with the page. Worth knowing, and DevOps's OPS-36: **the new part's
  markup is cached per site for 24 hours**, keyed on `assets.json`'s mtime. A
  real deploy bumps it; a hand `docker cp` and the local bench do not.
- **Permission enforcement points.** `notices_feed`'s two reads carry an explicit
  `for_user` **and** `document_type`; the grooming half goes through
  `grooming._readable` unchanged; `mark_all_seen`'s two filter terms are the whole
  control, because `frappe.db.set_value` with a dict filter checks nothing. The
  page enforces nothing and must not — every row it draws was already scoped by
  `inbox_api` or by Frappe's own condition.
- **Sensitive fields touched.** Grooming-mark and grooming-review subjects are
  **performance records** under counsel's 18 Sep 2026 rule. Approval rows carry a
  colleague's name, leave type, dates, claim amount and note, and
  `lwp_in_play` / `lwp_limit` are pay-adjacent. **Nothing new is read**: the field
  lists are `ROW_KEYS` and the notice item keys, both unchanged. No absence
  explanation, health, passport, bank, salary or Aadhaar anywhere near this page.
- **Nothing personal is logged.** The new code is a `COUNT`, a three-field read
  and an `UPDATE`. None handles a name or a subject, and none writes a log line.
- **Fallbacks.** Either call may fail alone and the other group still draws; the
  bell keeps its last number; the desktop bell falls back to our own CSS position
  if the navbar is not there; `drT()` falls back to the English string.

---

## 9 · Known gaps and shortcuts

Each labelled. A shortcut declared is a decision; a shortcut hidden is a defect.

| # | What | Label | What removes it |
|---|---|---|---|
| G-1 | **The Python suite has not run, so 23 new assertions and two edits are unexecuted** — including the three write assertions, which guard the riskiest lines in the slice | **dangerous debt — escalating now, not noting it** | One bench run, which needs either Docker up **and** the other session's two CSS files committed, or Surbhi's word on how to proceed. **Nothing in this slice should reach dev before that run is green** |
| G-2 | **AC-55's six-door list is not written** | **dangerous debt — escalating** | `hrms-test-automation-engineer`, on a fresh site, as a plain staff login. This is the ALV-249 canary |
| G-3 | AC-34's refusal is proved by pinning the decorator's numbers, not by exceeding the limit; the POST half **is** proved | **temporary debt** | One Python test with a real request |
| G-4 | AC-39 (one part of `get_nav_counts` raising) has no test | **temporary debt** | One Python test |
| G-5 | AC-54's four theme × brand contrast combinations, AC-50's Hindi, 200 % text and the bell at 1180 px are unseen | **temporary debt** | A browser pass as `ashok.mittal336@ppjewellers.demo`, which needs a running bench |
| G-6 | AC-45 / AC-46 show the server's sentence, not the prototype's two | **intentional trade-off — D-2, needs Surbhi's word** | Her decision either way |
| G-7 | AC-44's "first morning" is read as "has never had a notice", because no payload carries a joining date | **acceptable simplification — D-3, needs her word on the reading** | A new field, which the brief forbids |
| G-8 | A read-notice backlog beyond the first five is not reachable from this page | **acceptable simplification — D-9** | A fourth chip, refused upstream as UX-2 |
| G-9 | A work-call-only failure shows AC-38's words inside group 1 | **acceptable simplification — D-6** | Two new strings and their Hindi |
| G-10 | `update_modified=False`: nothing records **when** a bulk clear happened | **intentional trade-off**, accepted in spec §14 | An audit field and a statement per row |
| G-11 | `get_nav_counts` has never been measured in DTC's configuration | **temporary debt, named by DevOps as OPS-40's second half** | The fixture-site run in `07` §4.6 — **the test half is done** |
| G-12 | `portal.js` is now 24,575 lines and this slice added ~500 | **temporary debt**, pre-existing and made worse | Splitting the file, which is its own slice |
| G-13 | `Notification Log` rows are kept for ever, and a grooming-mark notice is a performance record | **pre-existing debt, accepted in writing by Surbhi 6 Nov 2026 for this slice only** | The purge engine (A6), the PM's to slice |
| G-14 | The five sidebar badges stay blank until their own panel opens, while the bell beside them is now trustworthy | **recorded, out of slice** (PM-8) | Its own slice. **Say it to DTC before they notice** |
| G-15 | The per-row `_dtc_row_facts` N+1, `_my_employee` asked twice, `inbox_api` never opening `call_cache` | **recorded, out of slice**, as the strategy said | Someone else's slice. I did not touch `inbox_api.py` |

**What I would fix with more time, honestly.** In order: run the Python suite —
everything else is noise beside 23 unexecuted assertions on a write that can
silently clear 597 people's notices. Then write AC-55. Then look at it in a
browser, because every statement about the badge's colour in this document is an
argument from a CSS token and not a thing anyone has seen.

---

## 10 · Subtract pass

Read again asking only *what can I delete and still meet the requirement?*
**Removed, in a commit of its own (`bd335de6`):**

- **`window.nfOpen` and `window.ntPaintBadge`.** Nothing outside `portal.js`
  calls either — `switchPanel` is in the same file, and the tests drive the page
  through the real route. `window.ntWorkOwed` stays, because the Home test
  asserts from a payload that the chip and the bell are computed by that one
  function.
- **A refusal branch in the new test's fetch stub.** I wrote it for a case I then
  covered better by re-asking the feeds. No test used it.
- **`.nf-list .hm-empty{border-top:0}`.** It can never match: an empty box is a
  sibling of the list box, not a child of it.

**Removed earlier, while building, rather than written and then deleted:**

- **A `parts/home.html` edit** for Home's sub-heading — one file fewer (D-7).
- **A new `nf-work` click target and a page-local row array.** The page and Home
  read the same payload, so the existing `pend` handler and `HM.rows` serve both;
  the page needed three new targets instead of eight.
- **A new skeleton rule and a second `prefers-reduced-motion` exemption.** The
  product's `.hm-skel` bar does it, resized by one line.
- **Five near-identical capped-work strings**, collapsed into one with the kind
  as a placeholder (D-4).
- **A `--on-primary` token** and the edits to `design_system.html` and
  `brand_color.html` that came with it — two files seven pages share (E-1).
- **A second bell element** for the desktop; one node, moved, has one id.
- **A `resize` listener** to re-home the bell between widths.
- **An `nf_api.py` module** for the count and the write.
- **A `NF_STALE_MS` and a refresh on returning to the page.**

**Kept despite the pass, each with a reason:** the three separate write
assertions, because a wrong write here is silent and one combined assertion would
not name the cause; the `my_requests > 0` fixture, because without it the test
that proves Home and the bell agree passes on a coincidence; `HM.askedPend` /
`HM.askedNotes`, because two booleans stop a slow Home being asked twice and
performance is this slice's known cost; and `NF.busy`, because the bulk write is
rate-limited and a double tap should not spend two of the thirty.

---

**Written by `hrms-fullstack-engineer`, 12 November 2026. Built locally, in a
worktree. Nothing pushed, nothing on dev, nothing deployed, and the Python suite
has not run. I recommend; Surbhi decides.**
