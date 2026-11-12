---
slice: 083-ess-notifications
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-06
status: draft — for Surbhi; four ⚠ DECISION rows below, none of which blocks the first day of work
inputs: [01-product-brief.md (approved 6 Nov 2026), 01a-ux-opportunities.md, 01b-ux-design.md (approved 6 Nov 2026), prototype-v1.html, 01c-security-privacy-requirements.md, 07-devops-inputs.md §1–§3, .claude/context/change-process.md, no-over-engineering.md, data-doors.md, product-context.md, frappe-conventions.md, nfr-budget.md, security-compliance-baseline.md, compliance-feature-map.md, definition-of-ready-done.md, handoff-contract.md, notices.py, inbox_api.py, grooming.py, portal.js, frame.html, field_app_limits.py]
ticket: ALV-322 (Epic, ALV project)
---

# 083 · A notifications bell and page — functional spec

## Answer first

**This slice is three small things and one dangerous line.** The three small things are
a bell on the laptop, a page with three filter chips, and a badge that counts work as
well as notices. The dangerous line is **"Mark all as read"** — a single `UPDATE` whose
filter is the only thing standing between one person's notices and everybody's.
**Confirmed fact** (01c §2): Frappe protects neither the count nor the write;
`frappe.db.count` returned **2,016** rows across 300-odd people when called with no
filter, and `frappe.db.set_value` checks nothing at all.

**Bad news, in order:**

1. **A wrong write is invisible.** Nothing logs a list read of `Notification Log`, and
   nothing at all logs the write. If the `for_user` term is lost, every colleague's
   notifications quietly turn read and **nobody would report it** (01c §1). That is why
   AC-30, AC-31 and AC-32 are three separate acceptance criteria rather than one.
2. **Nothing in this slice is observable on real data today.** PPJ holds **zero** rows
   of the three kinds the bell shows (Confirmed, 01b §2.3), and nobody has counted DTC.
   Every "0 findings" from a test run on PPJ today means nothing. Carried as **R6**, a
   kill criterion.
3. **One shipped number changes.** Home's "Pending for you" chip stops counting the
   person's own open requests (Surbhi's decision at the brief gate, PM-2 option A). An
   employee with one pending leave request will see a smaller number than yesterday.

**Rung 4 of the cost ladder, front end only** (`no-over-engineering.md`). Server code is
limited to exactly two things: a true uncapped `unread` plus a `capped` flag on
`notices_feed`'s return, and one bounded bulk mark-as-read **extended from a function
that already exists**. No new DocType. No new field. No new web address. No migration.

**I am not a lawyer.** Every point of law below is either counsel's already-given ruling
with its date, or a question marked for them.

---

## 1 · Cross-module reach — what this slice touches

| App / module | How it is touched | Risk if we are wrong |
|---|---|---|
| **`alvoraa_portal`** | `notices.py` (two keys on one return, one extended write), `public/js/ess/portal.js` (the page, the badge, Home's chip), `templates/includes/ess/frame.html` (desktop bell + sidebar item), `public/css/ess/frame.css` and `panels.css` | The whole slice lives here |
| **`alvoraa_portal.grooming`** | `my_notices_seen` (`grooming.py:1035`) is **extended** to cover `Announcement`; `_readable` is called on more rows than before (unread ones outside the page's 100) | A dropped filter term in the write; a slower `_readable` call (costed by DevOps as **zero extra queries**, §2.1) |
| **`alvoraa_portal.inbox_api`** | **Read only, unchanged.** `get_nav_counts` is called from one more place (every non-Home page). `ROW_KEYS` is **not touched** | A privacy regression if the bell ever calls `get_inbox` instead (OPS-1) |
| **`hrms`** | Nothing changed. Rows are read from Leave Application, Expense Claim, Attendance Request, Shift Request through `inbox_api`'s existing scope | — |
| **`erpnext`** | Nothing changed. `Employee.status` is read by the existing scope helpers | — |
| **`frappe`** | **Nothing changed.** `Notification Log` is read and written through Frappe's own APIs. **No upstream edit** | A `Custom DocPerm` would be an upstream-adjacent change — explicitly refused (01c R3) |
| **`alvoraa_goals` / `alvox_compensation`** | **Not touched.** Goal and KPI updates reach the page only through `inbox_api`'s existing `goal_updates` part | — |
| **New app** | **None.** |

**HRMS domains involved:** leaves (approval rows), attendance (correction rows),
appraisals / goals (goal and KPI update rows), org structure (`reports_to` decides whose
grooming notice is readable), learning — not involved. Payroll — not involved, except
that `lwp_in_play` / `lwp_limit` appear on a leave row where a pay rule set is on
(Confirmed, `inbox_api.py:124`).

**Mobile:** nothing. The phone is a PWA over the same portal (Surbhi, 24 Oct 2026). No
mobile artifact, no Flutter work. **Constraint.**

---

## 2 · Did we question the ask?

**The brief's problem is the real one, and I checked rather than assumed.**

| Check | Finding |
|---|---|
| **Symptom or cause?** The stated symptom is "a laptop manager gets no signal". | **Cause confirmed in code**, not inferred: `frame.css:231` sets `.mob-header{display:none}` and panels.css turns it on only below 768 px, so the bell markup and its call exist on desktop and the element is hidden. This is a cause, not a symptom. |
| **What decision does the screen drive?** | A leave or expense **approval**, taken from the page itself through the existing sheets. Not a dashboard. **Confirmed fact:** `hmDropPending` (`portal.js:6799`) already drops the row and decrements the count, so the decision loop closes without new code. |
| **Could the system act instead of displaying?** | No, and it must not. The decision is a human's by design (§13.4). The only automation worth having — "tell them on their phone before they open the portal" — was rejected in the brief §3a because 441 DTC logins share handsets. **I agree and am not reopening it.** |
| **Is any part of this a screen nobody acts on?** | One candidate: the third group, "Waiting on someone else". It is **not** actionable by design. It stays because it is the only answer in the product to "where has my leave request got to?" and it is the price of taking those rows **out** of the badge. It is explicitly labelled *not counted*. |
| **Anything the brief asked for that we should drop?** | Yes — one. See the gap analysis, row G-14. |

---

## 3 · Gap analysis — what already exists, what we configure, what we build

Every "standard behaviour" cell quotes something I read in the source in this worktree
at `814d540f`. **Confirmed fact** unless labelled otherwise.

| # | Requirement | What the installed apps do today | Verdict | Cost |
|---|---|---|---|---|
| G-1 | A bell with a count, visible on a laptop | The markup exists (`frame.html:135`, `#mob-notif-btn`), the call already runs on every page (`ntBellBoot`, `portal.js:18393`), one CSS line hides it (`frame.css:231`). **Frappe's own notification bell is a Desk UI and ESS staff have no Desk** — which is why slice 076 had to build this one | **Configure + Extend** (CSS and ~15 lines of markup; place it in Frappe's website navbar, right of the avatar) | **S** |
| G-2 | A page with an address that survives reload and Back | `mayOpenPanel` (`portal.js:4707`) resolves a panel only by finding a **visible** `.nav-item[data-panel=…]`; anything else is replaced with `#home`. So the page needs a visible sidebar item or it has no address | **Extend** — one nav item, one panel | **S** |
| G-3 | Filters over the notices and work the page already holds | No filter of any kind exists on either surface. `notices_feed(see_all=1)` already returns the window (last 30 days, unread first, `READ_CAP = 100`) | **Extend** — three chips, filtering an array in the browser. **No server change** (OPS-5, closed) | **S** |
| G-4 | A badge that counts work owed as well as unread notices | `ntPaintBadge` (`portal.js:6825`) paints notices only. `get_nav_counts` returns the per-part counts and **is wired into nothing in the live portal** (Confirmed, DevOps §1) | **Extend** — sum two existing answers in the browser; one paint function, three call sites | **S** |
| G-5 | A true unread count, not a capped one | `notices_feed` computes `unread` from `shown`, which came from a read capped at `READ_CAP = 100` (`notices.py:68–75`). A person with 150 unread gets `unread = 100` | **Extend** — +2 statements, split by kind (OPS-13). `Announcement` needs no gate; grooming rows fold into the `_readable` call the function already makes | **S** |
| G-6 | "Showing the first 100 notices" when the list was cut | `notices_feed` returns no `capped`. **The sibling endpoint already sets the standard:** `get_inbox` returns `cap`, `shown` and `capped` per part (`inbox_api.py:1186–1188`) | **Extend** — one key on an existing return | **S** |
| G-7 | Mark all my notices as read, in one call | **It already exists.** `grooming.my_notices_seen` (`grooming.py:1035`) is one `frappe.db.set_value` with `for_user`, `read = 0` and `document_type in (MARK, REVIEW)` — and DevOps confirms the portal no longer calls it. Frappe's own `mark_all_as_read` (`notification_log.py:271`) filters on `for_user` **only**, so it would clear rows this page never showed | **Extend the existing function** to cover `Announcement` (add one constant to one tuple). **Rung 1–2, not rung 4** | **S** |
| G-8 | A rate limit on that write | **It already exists.** `field_app_limits._limited(SELF_KEY, "user", limit=N)` — per hashed user, 3600 s window, POST only — on seven endpoints already | **Configure** — one decorator line at `limit=30` (OPS-22) | **S** |
| G-9 | Per-notice read state | **Frappe owns it.** `Notification Log.read`, written by Frappe's own `mark_as_read(docname)`, which only ever changes a row whose `for_user` is the caller | **Already there** | **—** |
| G-10 | Approve or decline from the page | `hmLeaveSheet` / `hmExpenseSheet` exist, re-check permission server-side, and already decrement the count on success | **Already there — reuse only.** If the reuse is not clean, drop it to later rather than write a second sheet (brief §5 item 11) | **—** |
| G-11 | Per-task "seen" / dismiss / snooze | Nothing exists, and nothing should. It needs a new field for a behaviour nobody asked for | **Drop — and never** (brief §8.3 rule 1) | **—** |
| G-12 | A merged `notifications_feed` endpoint with server-side filters and paging | Two endpoints already answer this. A third filter expression over the same data is what `inbox_api`'s own docstring forbids, and a new address would need `deploy/nginx.conf` edited — the one file that serves production | **Drop** (brief §3a, OPS-4, OPS-23) | **—** |
| G-13 | Who read my announcement | `Notification Log.read` makes it trivial, which is exactly why it is refused. The security engineer is the named decider and has ruled **no** per named recipient (01c §7) | **Drop — out of scope, its own slice with counsel** | **—** |
| G-14 | Success measure 1 — "share of approvals decided from the notifications page" (brief §12) | **There is no field that records which screen raised a decision.** I grepped: the decision endpoints take the document and the action, not a source. Measuring it needs a new field | **Drop the measure, not the slice.** The brief itself says "⚠ if it needs a new field, drop this measure rather than add one". I am taking it at its word. **⚠ DECISION BA-1** for Surbhi to confirm | **—** |
| G-15 | Fix the five stale sidebar badges with `get_nav_counts` | `get_nav_counts` has no caller; five badges paint only after their panel opens | **Drop — separate slice** (PM-8, Surbhi's instinct, PM agreed). Say out loud: after this slice the bell is visibly more trustworthy than those five | **—** |
| G-16 | A retention / purge rule for `Notification Log` | **Nothing trims it. Rows are kept for ever** (Confirmed: Frappe's `clear_notifications` deletes redis keys, not rows). A grooming-mark notice **is** a performance record under counsel's binding 18 Sep 2026 policy | **Drop from this slice; carry as named debt.** PRIV-5 / **⚠ DECISION SEC-R1** | **—** |
| G-17 | A cache of the badge number | `call_cache` dies with the call. A cross-request cache needs ~15 invalidation paths plus permission changes that cannot be hooked, against a measured p95 of 215 ms on a 500 ms budget | **Drop** (OPS-11) | **—** |

### Where two things describe the same number — the single source of truth

| The thing | Single source of truth | How the other stays in step |
|---|---|---|
| "How many unread notices?" | **`notices.notices_feed().unread`** — after this slice, the true uncapped count | Home's chip, the bell and the page all read this one answer. Nothing else counts notices (`notices.py` docstring) |
| "How much work is waiting on me?" | **`inbox_api.get_nav_counts().parts[].count`**, summed in the browser, skipping `shift_requests` and `my_requests` | Home's chip and the bell use **one** function. See AC-11 |
| "What may this person read?" | **Frappe's permission condition on `Notification Log`** + `grooming._readable` + `get_inbox`'s per-part scope | Our page adds nothing and **must not be where the limit lives** |
| The badge number | **One function, `ntPaintBadge(workOwed + unread)`** | Three call sites only: Home's paint, `ntBellBoot`, and after a decision. A second place that computes the number is a defect (AC-12) |

---

## 4 · Process flow

### 4.1 The sunny day — a line manager on a laptop

1. Sakshi opens the portal on her laptop and goes to **Attendance** (not Home).
2. The frame loads. ~1.5 s later the bell boot fires two calls together:
   `notices.notices_feed(see_all=0)` and `inbox_api.get_nav_counts()`.
3. The browser adds: *work owed* (every part count except `shift_requests` and
   `my_requests`) **+** *unread notices*. The bell paints **7**.
4. She clicks the bell (or the sidebar item). The address becomes
   `/hrms-employee#notifications`.
5. The page draws a skeleton inside 300 ms, then: **"4 waiting on you"**, then
   **"Notices · 3 unread"** with *Mark all as read*, then **"Waiting on someone else ·
   not counted — nothing for you to do yet"**.
6. She taps Rakesh's leave row. The existing leave sheet opens **in place**.
7. She approves with a reason. **Decision point:** the server re-checks her permission.
8. On success the row leaves, the heading reads "3 waiting on you", and the badge falls
   to **6** — one paint, one number.
9. She taps *Mark all as read*. The three unread notices lose their dot, the heading tag
   goes, and the badge falls to **3**.

### 4.2 The unhappy paths — each one is a state in the prototype

| # | What goes wrong | What the person sees | Writes anything? |
|---|---|---|---|
| U-1 | **The notices call fails, the work call succeeds** | Group 1 draws normally. An amber box **inside the notices group only**: "Could not load your notices." / "Your work is shown below. Nothing has been lost." · *Try again*. **The bell is unchanged. No toast.** | no |
| U-2 | **Both calls fail** | One amber box, no groups: "Could not load this page." / "Check your connection and try again. Nothing has been lost." · *Try again* | no |
| U-3 | **A call times out** | The same box as U-2 or U-1. **A spinner always ends.** | no |
| U-4 | **She taps a row somebody else already decided** | The server refuses. The page shows **"Already decided by someone else."** and removes the row. Never a raw error, never a silent no-op | the server's own refusal; no write |
| U-5 | **She taps a row the employee withdrew** | **"The request was withdrawn."**, row removed | no |
| U-6 | **The row stopped being hers** (she no longer manages Rakesh) | **Nothing is said.** The row is simply gone on the next load. "You no longer approve for Rakesh" would leak an org change | no |
| U-7 | **Her inbox is capped** (HR, 63 attendance fixes) | Footer inside group 1: "Showing the first 50 of 63 attendance fixes" | no |
| U-8 | **Her notices are capped** (150 unread) | Footer inside group 2: "Showing the first 100 notices. Older read ones are not kept." The **badge still shows the true count** | no |
| U-9 | **She has nothing at all** | One green tick box: "Nothing waiting on you, and no new notices." | no |
| U-10 | **First morning, a new joiner** | One box that says what the page is *for*: "Nothing here yet." / "This is where you will see anything waiting on you…" | no |
| U-11 | **She presses the bulk clear 31 times in an hour** | The server refuses in a sentence through `frappe.throw` (`TOO_MANY_TRIES`), shown by the portal's own error handler | no |
| U-12 | **Guest, or a session that expired** | `/hrms-employee` redirects to `/alvoraa-login?redirect-to=/hrms-employee` before any context is built | no |
| U-13 | **The next person picks up the handset after sign-out and presses Back** | **Nothing renders.** | no |
| U-14 | **A notice's document was deleted or is no longer readable** | The row is simply absent (`grooming._readable` drops it) and the count drops with it | no |
| U-15 | **A work row has no `waiting_since`** | The row draws **without** a waiting line. Never "waiting undefined days" | no |

---

## 5 · Epic and user stories

**Epic (ALV-322):** *A notifications bell on every screen and a page that tells an
employee what is waiting for them, in one number they can clear by doing the work.*

Personas from `product-context.md`: **Employee**, **frontline employee on a shared
handset**, **Line manager**, **HR Manager**, **CXO**.

| ID | Story | Persona | Points | Prototype screen / state | Requirements carried | ACs |
|---|---|---|---|---|---|---|
| **US-1** | *As a line manager on a laptop* I want a bell with a number in the top bar on every screen, *so that* I know something is waiting without going Home first | Line manager | 2 | Desktop 1180 px · navbar | OPS-4, OPS-23 | AC-1, AC-2, AC-3 |
| **US-2** | *As an employee* I want "Notifications" in the sidebar, *so that* I can reload the page or press Back and still be on it | Employee | 2 | Desktop · sidebar, after Home/Attendance/Leave (amended 12 Nov) | — | AC-4, AC-5, AC-6 |
| **US-3** | *As an employee* I want one page with work first, then notices, then my own requests, *so that* I never have to pick a tab before finding my work | Employee, frontline | 5 | "Notifications page" · Loaded | — | AC-7, AC-8, AC-9, AC-10 |
| **US-4** | *As a frontline employee in a hurry* I want three chips — All, To do, Unread notices — *so that* I can get to just my work in one tap | Frontline | 2 | all five people · chips | OPS-5 | AC-13, AC-14, AC-15 |
| **US-5** | *As an HR Manager with 86 unread notices* I want each group capped at five rows under All with the real total named, *so that* the page is not 6,744 px tall and I can still reach the third group | HR Manager | 2 | "HR Manager — a busy inbox (capped)" | — | AC-16, AC-17, AC-18 |
| **US-6** | *As an employee* I want one number that counts unread notices **and** work owed, *so that* I can trust it and watch it fall as I work | Employee, Line manager | 3 | yellow arithmetic line, all states | OPS-1, OPS-8, OPS-11 | AC-11, AC-12, AC-19, AC-20 |
| **US-7** | *As an employee* I want Home's "Pending for you" number to mean exactly what the bell means, with my own requests under their own sub-heading, *so that* two screens never disagree | Employee | 3 | "Home — the changed card" | — | AC-21, AC-22, AC-23 |
| **US-8** | *As an HR Manager with 150 unread notices* I want the badge to show the true number and the page to say when the list was cut, *so that* the badge can reach zero when I have done everything the screen offered | HR Manager | 3 | capped-list line | OPS-13, OPS-28, SEC-1, PRIV-1 | AC-24, AC-25, AC-26, AC-27 |
| **US-9** | *As an HR Manager* I want "Mark all as read" in the notices group, *so that* clearing 86 notices is two taps, not 258 | HR Manager | 3 | "Mark all as read" | OPS-15, OPS-22, SEC-2, SEC-3 | AC-28, AC-29, AC-33, AC-34 |
| **US-10** | *As a line manager* I want to approve or decline from this page using the sheets I already know, *so that* I can act where I saw the problem | Line manager | 3 | "After approving two" | — | AC-35, AC-36 |
| **US-11** | *As an employee on a bad connection* I want the part that loaded to still show, and a Try again on the part that did not, *so that* one failure does not take the page down | Employee, frontline | 2 | "Notices failed, work loaded"; "Both calls failed" | OPS-6 | AC-37, AC-38, AC-39 |
| **US-12** | *As a new joiner on my first morning* I want the page to tell me what it is for rather than look broken, *so that* I trust it when something does arrive | Employee | 3 | "Loading"; "New joiner — first morning"; empty states | — | AC-40, AC-41, AC-42, AC-43, AC-44 |
| **US-13** | *As a line manager* I want to be told in plain words when a row has already been dealt with, *so that* I am not left wondering whether my tap worked | Line manager | 2 | "Stale row — already decided" | — | AC-45, AC-46, AC-47 |
| **US-14** | *As a CXO on a five-minute phone check* I want one row per kind and a badge that counts kinds, *so that* the number is 1–5 and moves when a queue empties | CXO | 2 | "CXO — counts by kind" | — | AC-48, AC-49 |
| **US-15** | *As a frontline employee who reads Hindi* I want every word on this page in my language, *so that* I can use it without help | Frontline | 2 | Language · हिन्दी, both widths | — | AC-50, AC-51 |
| **US-16** | *As an employee with poor eyesight, on a dark theme or a pale brand* I want the badge legible, *so that* I can read the number | Employee | 2 | Theme × Brand (4 combinations) | — | AC-52, AC-53, AC-54 |
| **US-17** | **(must not)** *As an employee* I must **not** be able to read a colleague's notice through any door — the API, the report view, an export, a link search or a share — *so that* nobody learns Rakesh got a grooming red | Employee | 3 | — | SEC-5, PRIV-2 | AC-55, AC-56 |
| **US-18** | **(must not)** *As an employee* my "Mark all as read" must **not** touch anybody else's rows, and must **not** touch my own Desk notifications this page never showed | Employee | 3 | — | SEC-2, SEC-4 | AC-30, AC-31, AC-32 |
| **US-19** | **(must not)** *As an employee* tapping something waiting on me must **not** mark it anything, *so that* the badge never goes quiet without the work being done | Employee | 1 | tap a work row | — | AC-57, AC-58 |
| **US-20** | **(must not)** *As the next person to pick up a shared handset* I must **not** see the previous holder's 30 days of HR messages | Frontline, shared handset | 3 | — | SEC-6, SEC-7, PRIV-3 | AC-59, AC-60, AC-61, AC-62, AC-63 |
| **US-21** | **(must not)** *As the person who gets paged at 2 a.m.* this slice must **not** add a timer, a queue, a worker, an alert, a secret or an nginx edit | — | 2 | — | OPS-21, OPS-23, OPS-25, OPS-26, OPS-27, OPS-28 | AC-64, AC-65, AC-66, AC-67 |

**Total: 48 points.** No story is an 8. **INVEST check:** US-3 is the only story near the
"small" edge (5) — it is the page itself and splitting it would leave half a screen, so
it stays whole and its four ACs are independently testable. US-19 is a 1 and could have
been folded into US-6; it stays separate because it is the rule the designer and the PM
both said must not be softened, and a rule inside another story gets traded away.

### YouTrack-ready table — **do not create these issues; that is Surbhi's call**

| Summary | Description (first line) | Persona | Points | ACs | Requirements |
|---|---|---|---|---|---|
| 083 US-1 Bell in the desktop navbar | Show the existing bell and its number on screens above 768 px, right of the avatar | Line manager | 2 | AC-1…3 | OPS-4, OPS-23 |
| 083 US-2 Notifications sidebar item | A visible `<button>` nav item so the hash route has an address | Employee | 2 | AC-4…6 | — |
| 083 US-3 The notifications page | Three groups in a fixed order, title and "Last 30 days" | Employee | 5 | AC-7…10 | — |
| 083 US-4 Three filter chips | All (default) · To do · Unread notices, filtered in the browser | Frontline | 2 | AC-13…15 | OPS-5 |
| 083 US-5 Five rows per group under All | "Showing 5 of 86" + "See all 86 notices" from the true count | HR Manager | 2 | AC-16…18 | — |
| 083 US-6 The merged badge | work owed + unread notices, one paint function, three call sites | Line manager | 3 | AC-11, 12, 19, 20 | OPS-1, 8, 11 |
| 083 US-7 Home's chip matches the bell | Same sum; own requests under their own sub-heading | Employee | 3 | AC-21…23 | — |
| 083 US-8 True unread count and capped flag | Uncapped `unread` + `capped` on `notices_feed` | HR Manager | 3 | AC-24…27 | OPS-13, 28, SEC-1, PRIV-1 |
| 083 US-9 Mark all as read | Extend `grooming.my_notices_seen` to Announcement; POST; limit 30/hour | HR Manager | 3 | AC-28, 29, 33, 34 | OPS-15, 22, SEC-2, 3 |
| 083 US-10 Decide from the page | Reuse `hmLeaveSheet` / `hmExpenseSheet` unchanged | Line manager | 3 | AC-35, 36 | — |
| 083 US-11 One call may fail alone | Draw what you have; amber box in its own group; Try again | Employee | 2 | AC-37…39 | OPS-6 |
| 083 US-12 Loading and the five empty states | Skeleton in 300 ms; first-morning wording | Employee | 3 | AC-40…44 | — |
| 083 US-13 Stale rows say why | "Already decided by someone else." / "The request was withdrawn." / silence | Line manager | 2 | AC-45…47 | — |
| 083 US-14 The CXO shape | Counts by kind, badge = kinds + unread | CXO | 2 | AC-48, 49 | — |
| 083 US-15 Hindi at parity | Every new string through `drT()`; native reader sign-off | Frontline | 2 | AC-50, 51 | — |
| 083 US-16 Badge size and colour | 12 px in `.notif-badge`; `--primary` on `--on-primary` | Employee | 2 | AC-52…54 | — |
| 083 US-17 **must not** read a colleague's notice | The door list as a plain staff login on a fresh site | Employee | 3 | AC-55, 56 | SEC-5, PRIV-2 |
| 083 US-18 **must not** write past my own notices | Three separate assertions on the bulk write | Employee | 3 | AC-30…32 | SEC-2, SEC-4 |
| 083 US-19 **must not** mark work owed | Tapping work owed sends no request | Employee | 1 | AC-57, 58 | — |
| 083 US-20 **must not** leave anything on the handset | No client storage; Back after logout renders nothing | Frontline | 3 | AC-59…63 | SEC-6, 7, PRIV-3 |
| 083 US-21 **must not** grow an operational tail | No timer, queue, worker, alert, secret or nginx edit | — | 2 | AC-64…67 | OPS-21, 23, 25, 26, 27, 28 |

---

## 6 · Data model

### 6.1 New DocTypes and fields: **none**

| Question | Answer |
|---|---|
| New DocType? | **No.** |
| New field, Custom Field or property setter? | **No.** The one thing that would need storage is a per-task "seen" flag, and §8.3 rule 1 of the brief says we never have one |
| New child table? | **No.** |
| New table, index or migration? | **No.** The composite index `(for_user, read, document_type)` was considered by DevOps and **rejected** — no measured number misses the budget (OPS §2.11) |
| New whitelisted method? | **At most one**, and only if the extended `my_notices_seen` is moved rather than reused in place. SEC-3 caps the growth at +1 |

### 6.2 DocTypes read and written

| DocType | Read | Written | By what | Permission door |
|---|---|---|---|---|
| **Notification Log** (Frappe core) | `name`, `subject`, `link`, `creation`, `read`, `document_type`, `document_name` — for `for_user = session user` and `document_type in (Grooming Mark, Grooming Review, Announcement)` | **`read` 0 → 1 only**, for the caller's own rows of those three types | `notices.notices_feed`; the extended `my_notices_seen`; Frappe's own `mark_as_read` for one row | `get_permission_query_conditions` at `notification_log.py:104` and `has_permission` at `:114`, hooked at `frappe/hooks.py:117` and `:151`. **Confirmed by running the door list** (01c §2). **Neither the count nor the bulk write is covered — the filter terms are the whole control** |
| **Grooming Mark / Grooming Review** | `employee`, `mark_date`, `owner` for readability | never | `grooming._readable` | `_readable` + `_active_employee` (`status = "Active"`) |
| **Announcement** | `name`, `sender_label` | never | `notices_feed` | bounded to the caller's own announcement rows |
| **Leave Application, Expense Claim, Attendance Request, Shift Request, Policy Document, Individual Goal, KPI** | the `ROW_KEYS` fields below | **only through the existing decision sheets**, which re-check permission server-side | `inbox_api` per-part scope: `permitted_companies`, `permitted_employees`, named-approver filter, and `no_rows()` returning `{"name": ["in", []]}` so "entitled to nobody" never means "everybody" | unchanged by this slice |

### 6.3 The two changed keys on `notices_feed`'s return

| Key | Today | After | Why no existing key carries it |
|---|---|---|---|
| `unread` | `len([r for r in shown if not r.read])` — counted from a list capped at `READ_CAP = 100` | **the true count** of unread notices the caller may still read, uncapped: one `COUNT` for unread Announcements (no gate needed) plus the readable part of one uncapped three-field read of unread grooming rows, folded into the `_readable` call the function already makes (OPS-13) | The key exists; its value is wrong at volume. A second key would give the badge two sources |
| `capped` | absent | `True` when the page's own read hit `READ_CAP` | Nothing on this return says the list was cut. **`get_inbox` already returns `cap`, `shown` and `capped` per part** for exactly this reason — this is consistency, not invention |

**Unchanged and frozen (PRIV-1):** the item keys stay exactly `name`, `kind`, `from`,
`text`, `link`, `when`, `read`, and the top-level keys stay `unread`, `any`, `can_send`,
`items` — plus `capped`. Nothing else leaves the server.

### 6.4 Parity table — the **full** per-part field list

**This table replaces the design's six-word summary.** The design §6.2 says rows carry
"Name · kind · dates · days · amount · waiting N days". That is **shorter than the real
set**, and the security engineer asked explicitly for the real one so PRIV-1's test
asserts the fields that actually exist. Read from `inbox_api.py:112–167` today.

| Part | Every field a row may carry (`ROW_KEYS`, unchanged) | Sensitivity | Drawn on the page? |
|---|---|---|---|
| `leave_approvals` | `name`, `employee_name`, `from_date`, `to_date`, `leave_type`, `total_days`, `context`, `action`, `waiting_since`, `half_day`, `lwp_in_play`, `lwp_limit`, `special_day`, `chain_top` | colleague personal; `lwp_in_play` / `lwp_limit` are **pay-adjacent** and appear only where a pay rule set is on | name, kind, dates, days, waiting line. The rest reaches the **decision sheet**, which is unchanged |
| `expense_approvals` | `name`, `employee_name`, `expense_type`, `expense_date`, `amount`, `note`, `waiting_since`, `has_bill`, `action` | colleague financial. **`has_bill` is a boolean — never a filename, never a URL** (slice 081) | name, amount, type, waiting line, and "Bill attached" / "No bill attached" in words |
| `goal_updates` | `name`, `kind`, `employee_name`, `subject`, `logged_on`, `value`, `action`, `waiting_since`, `document` | colleague performance | name, kind, subject |
| `attendance_fixes` | `name`, `employee_name`, `from_date`, `to_date`, `reason`, `context`, `action`, `can_decide`, `waiting_since` | internal, low. **`reason` is the fixed-option category the employee picked, not free text** — the free-text field is `explanation` and **it is not in `ROW_KEYS`** (Confirmed, 01c §3) | name, dates, waiting line |
| `shift_requests` | `name`, `employee_name`, `from_date`, `to_date`, `shift_type`, `action`, `waiting_since` | colleague internal | **not drawn and not counted** — no screen exists where a manager decides a shift change |
| `policies` | `name`, `title`, `version`, `action`, `waiting_since` | not personal at all — a policy is a document | title, version |
| `my_requests` | `name`, `kind`, `title`, `from_date`, `to_date`, `state`, `says`, `note`, `can_withdraw`, `action`, `waiting_since` | the caller's own | title, dates, the state sentence. **Drawn in group 3, not counted** |
| notice row | `name`, `kind`, `from`, `text`, `link`, `when`, `read` | grooming subjects are **performance records**; announcements are internal | sender, time, text, unread dot |

**What is absent, and checked field by field** (01c §3): no absence explanation, no
health, no passport, no bank, no account, no salary, no pay figure, no Aadhaar, no photo,
no `document_name` on a notice row, and no file name or URL anywhere.

### 6.5 Where the spec departs from the prototype — **⚠ needs Surbhi's approval**

Per the prototype-parity rule (21 Oct 2026): every difference is listed, or there is no
difference.

| # | Prototype draws | The spec says | Why | Needs Surbhi? |
|---|---|---|---|---|
| P-1 | Under "All", the notices heading is **"Notices"** with a tag **"3 unread"**; under the Unread chip it is **"3 unread notices"** | the same | This is the designer's own named divergence from the brief's §6 micro-copy (⚠ UX-1), carried forward because a heading must name its own list | **DECIDED by Surbhi, 6 Nov 2026: "Notices · 3 unread".** The designer's wording stands; the brief's §6 micro-copy is superseded |
| P-2 | The desktop nav item sits **second, after Home**, with a bell icon, the word, and the badge | the same | — | no |
| P-3 | The prototype's sidebar shows **word labels**; the live desktop rail is **icon-only, 35 px, no label** (Measured, 01b M8) | **The new item carries the word** — a nav item nobody can see or name cannot be found, and `mayOpenPanel` needs it visible | A real, visible difference from the live product, drawn deliberately by the designer | **DECIDED by Surbhi, 6 Nov 2026: approved.** The new item is allowed to be the only labelled one on the rail. Labelling the whole rail stays a separate slice |
| P-4 | The prototype's phone bar reads **"PP Jewellers"**; the live bar truncates the tenant name | the live behaviour stands; brand on screen is **"Alvora"**, one trailing a, where the product names itself | the prototype shows a tenant, not the brand | no |
| P-5 | "Mark all as read" in the HR case says it marked **the 100 the page holds** | After US-8, the write is **set-based and reaches every unread notice of the three kinds**, so it really does mean "all". The prototype's own note flags this as ⚠ UX-4 | The prototype predates the write being settled | no — the spec is the stricter answer |
| P-6 | The CXO work group carries a tag **"counts by kind"** | the same | — | no |
| P-7 | The prototype has a **review bar and a yellow arithmetic line** | **not built.** They are scaffolding (`data-px-*`) | obvious | no |
| P-8 | The prototype's phone bottom bar has **three** items | the same — **no fourth item** | Measured: a fourth takes each from 129 px to 97 px | no |

**Everything else in the prototype is specified as drawn.** Five people, six states, two
widths, two themes, two brands and two languages all appear in §9's ACs.

---

## 7 · States and transitions

**There is no workflow, and this slice adds none.** There is exactly one state machine,
and Frappe already owns it.

| Object | State | Who may change it | Next state | What becomes read-only | What is notified | Reversible? |
|---|---|---|---|---|---|---|
| **A notice** (`Notification Log.read`) | `read = 0` (unread) | **the recipient only** — by opening it, or by "Mark all as read" | `read = 1` | nothing | **nothing. No notification is sent by this slice, ever** | **No, and deliberately.** There is no "mark unread". The designer refused a confirm dialog on the bulk clear because it destroys no work — the notice text stays and the row stays reachable under "All" for 30 days |
| **A notice** | `read = 1` | — | **terminal** for this slice | — | — | — |
| **Work owed** (a leave application, a claim, a correction, a policy) | not this slice's | the existing approval flow, unchanged | not this slice's | not this slice's | by the existing flow | — |

**Work owed has no state in this slice at all.** It leaves the list for exactly three
reasons, each with its own message:

| Reason it left | Message |
|---|---|
| The person did the work | the row leaves on success; the heading and the badge fall |
| Somebody else decided it | **"Already decided by someone else."** |
| The requester withdrew it | **"The request was withdrawn."** |
| *(fourth case)* it stopped being theirs | **nothing is said.** It is simply gone on the next load |

**There is no dismiss, no snooze, no swipe, no X and no "mark done" on a work row. Not
in v1, not later.**

---

## 8 · Permission and visibility matrix

Built from 01c §4. **The Frappe door is named for every rule, because our page is not
the security.**

### 8.1 Role × object × operation

| Object | Operation | CXO (System Manager) | HR Manager | Line manager | Employee / frontline | Guest | The door that enforces it |
|---|---|---|---|---|---|---|---|
| **Notification Log** — own rows, three notice types | read | own only | own only | own only | own only | **none** | `get_permission_query_conditions` (`notification_log.py:104`) + `has_permission` (`:114`). **Verified by running the full door list** |
| **Notification Log** — a colleague's row | read | **no** | **no** | **no** | **no** | no | the same `for_user` pin. Being a manager, HR, or a System Manager is **not a term in the condition** |
| **Notification Log** | write `read` 0→1 | own rows, three types only | same | same | same | no | **the `for_user` + `document_type` filter terms in our own code. Frappe checks nothing here** — SEC-2 |
| **Notification Log** | create, delete, submit, cancel | **nobody, from this slice** | nobody | nobody | nobody | nobody | the doctype grants role `All` only `read, report, export, print, email, share` — **no write, no create, no delete**; `Custom DocPerm` is empty (Confirmed) |
| **Notification Log** | export (CSV) | own row only | own row only | own row only | own row only | no | `reportview.export_query` runs the same condition; `DISALLOWED_PARAMS` strips `ignore_permissions` and `user`. **Verified by running it** |
| **Notification Log** | share | **own row only** | own row only | own row only | own row only | no | `has_permission(..., "share", doc=<colleague's row>)` returned `False`. A `DocShare` of one's **own** row is possible — accepted as **R3, P4** |
| **Approval rows** (`get_inbox` parts) | read | **counts by kind only, no names** | rows inside `permitted_companies` | only rows where they are the named approver | **none** unless they are an approver | none | `get_inbox`'s per-part scope, unchanged by this slice |
| **Approval rows** | decide | nothing from this page | correct and decide across their companies | approve / decline with a reason | — | — | the existing decision endpoints, which re-check server-side |
| **Own request rows** (`my_requests`) | read | own | own | own | own | none | the per-part scope. **Never a colleague's request** |
| **Own request rows** | withdraw | where already allowed | same | same | same | — | unchanged |
| **Policies to acknowledge** | read / acknowledge | published to them | same | same | same | none | unchanged |
| **The page itself** (`#notifications`) | open | yes | yes | yes | yes | **redirected to `/alvoraa-login`** | `www/hrms_employee.py`, before any context is built. **Verified by curl** |

### 8.2 The negative cases, stated explicitly

These are the sentences a reviewer should be able to read back to me.

1. **An HR Manager must not see a colleague's notice row through this page.** This page is
   the person's own inbox, not an HR tool. HR's wider scope lives in `grooming` and
   `hr_api`, not here.
2. **A line manager must not see their team's notices.** Being somebody's manager is not
   a reason to read their grooming alert.
3. **A CXO must not receive 400 colleague names in a bell payload.** The bell takes
   `get_nav_counts` (numbers), never `get_inbox` (rows) — OPS-1.
4. **An announcement sender must not learn who read their notice.** No endpoint, payload
   or log returns per-recipient read state to anyone but the recipient — PRIV-4.
5. **An employee who is not an approver must not see any approval row.**
6. **A leaver with a live login must reach nothing.** `_active_employee`, `hr_scope` and
   `_my_employee` all filter `status = "Active"` (Confirmed in three places).
7. **A manager who stopped managing somebody must lose that row silently.** The row is
   gone; the screen says nothing, because "you no longer approve for Rakesh" leaks an
   org change.
8. **No outside party — auditor, agency, vendor — gets anything.** There is no share, no
   print route and no export on this page.
9. **The next holder of a shared handset must see nothing.**
10. **The bulk write must not reach one row outside the caller's own three notice
    types** — including the caller's own `document_type = "Employee"` Desk rows. PPJ's
    heaviest user carries **406** of them.

### 8.3 Who may read and write each field, per persona

| Field group | Employee / frontline | Line manager | HR Manager | CXO | Sender |
|---|---|---|---|---|---|
| own notice `text`, `from`, `when`, `kind`, `link` | read own | read own | read own | read own | — |
| own notice `read` | **read and write own** | own | own | own | **never** |
| approval row identity fields (`employee_name`, `title`) | — | read, own named rows | read, own companies | **no names — counts only** | — |
| approval row decision fields (`leave_type`, dates, `total_days`, `amount`, `note`, `has_bill`, `reason`, `context`, `value`, `subject`, `logged_on`, `state`, `says`, `can_decide`, `can_withdraw`, `document`, `action`, `waiting_since`) | — | read, own named rows; write only through the existing decision endpoint | read, own companies; same | no | — |
| `half_day`, `lwp_in_play`, `lwp_limit`, `special_day`, `chain_top` | — | **read** — it is the thing being decided; only where a pay rule set is on | read, own companies | no | — |
| `my_requests` fields | read own | read own | read own | read own | — |

---

## 9 · Acceptance criteria

Every one has an observable oracle. Every one belongs to a story.

### US-1 · The bell on desktop

- **AC-1** · *Given* a signed-in employee on a window **1180 px wide**, *when* they open
  any portal screen that is not Home, *then* a bell button is visible in the top bar at
  the right end, **immediately left of the avatar**, with a hit area of **at least
  36 × 36 px**, and its accessible name reads **"Notifications, 7 waiting"** for a badge
  of 7.
- **AC-2** · *Given* the same window, *when* the two calls have answered, *then* the
  badge is drawn **outside** the bell glyph at its top-right corner, 18 × 18 px, and
  shows **"99+"** for any number above 99.
- **AC-3** · *Given* the badge number is **0**, *when* the page paints, *then* the badge
  element is **not displayed** and the bell's accessible name carries 0.

### US-2 · The sidebar item

- **AC-4** · **AMENDED by Surbhi, 12 November 2026.** *Given* the desktop sidebar, *then* a
  nav item labelled **"Notifications"** is visible **after Home, Attendance and Leave**,
  carrying a bell icon, the word, and the same badge number.

  It was written as the **second** item, straight after Home, which is how the approved
  prototype draws it. CI caught the conflict: **slice 060 had deliberately pinned
  Attendance second**, and said why in its own test — *"the thing people open most should
  not be eighth"*. That decision was approved too, and this slice never asked to displace
  it. Surbhi kept 060's order: the bell in the top bar is the way in on every page, so this
  item is mainly the page's **address** and its label, and buying it a higher position by
  pushing Attendance down is a worse trade. **The prototype is now out of date on this one
  point, deliberately and with her word.**
- **AC-5** · *Given* the person is on `/hrms-employee#notifications`, *when* they
  **reload** the page, *then* the notifications page is shown — **not** Home. *(Oracle:
  `mayOpenPanel("notifications")` returns true because a visible nav item exists.)*
- **AC-6** · *Given* the nav item, *when* it is reached by **Tab**, *then* it receives
  focus with a 3 px `--primary` outline and **Enter** opens the page. *(It is a real
  `<button>`; the other sixteen `<div onclick>` items are left to their own slice.)*

### US-3 · The page

- **AC-7** · *Given* the page is loaded, *then* it shows the title **"Notifications"**
  and, beneath it, **"Last 30 days"**.
- **AC-8** · *Given* the page is loaded with work, notices and own requests, *then* the
  groups appear in this order and **the order never changes with the filter**:
  (1) **"{N} waiting on you"**, (2) **"Notices"** with tag **"{N} unread"**,
  (3) **"Waiting on someone else"** with tag
  **"not counted — nothing for you to do yet"**.
- **AC-9** · *Given* group 1 holds rows of more than one kind, *then* they are ordered
  **oldest `waiting_since` first across kinds**, the order Home already uses.
- **AC-10** · *Given* a row in group 3, *when* it is reached by keyboard or tapped,
  *then* **nothing happens** — it is not a button. Its state sentence is the answer.

### US-6 · The number

- **AC-11** · *Given* `get_nav_counts` returns part counts
  `leave_approvals 2, expense_approvals 1, goal_updates 0, attendance_fixes 1,
  shift_requests 3, policies 0, my_requests 2` and `notices_feed` returns
  `unread = 3`, *then* the badge reads **7** — the sum of the `parts[]` counts **skipping
  `shift_requests` and `my_requests`**, plus `unread`. *(Oracle: the rendered badge text.
  The test must also assert the badge is **not** 12 (`d.total − shifts` + unread) and
  **not** 10 (`approvals_total` + unread) — the two wrong answers.)*
- **AC-12** · *Given* the built portal JavaScript, *then* **exactly one** function
  computes and paints the badge, and it is called from exactly three places: Home's
  paint, `ntBellBoot`, and after a decision. *(Oracle: a source assertion counting
  writes to the badge element.)*
- **AC-19** · *Given* the page is drawn, *then* **badge = (rows counted in group 1) +
  (unread notices in group 2)**, and group 3's rows are in **neither**. *(Oracle: a DOM
  test that reads the two headings' numbers and the badge and asserts they reconcile.)*
- **AC-20** · *Given* `notices.NOTICE_DOCTYPES` and the seven doctypes `inbox_api`'s
  parts read, *then* the two sets are **disjoint**, asserted in a test that fails if
  anyone adds a doctype to either side. *(OPS-8. They are disjoint today — Confirmed.)*

### US-7 · Home agrees with the bell

- **AC-21** · *Given* the same payload as AC-11, *when* Home paints, *then* the "Pending
  for you" chip reads **"4 waiting"** — the same `work owed` sum as the bell, **not**
  `d.total − shift_requests`.
- **AC-22** · *Given* Home's "Pending for you" card and a person with two open requests
  of their own, *then* those rows appear under a sub-heading inside the same card reading
  **"Waiting on someone else · not counted — nothing for you to do yet"**, below the
  approval rows.
- **AC-23** · *Given* any payload, *then* **the Home chip and the bell show the same
  number** on the same load. *(Oracle: one test that paints both and asserts equality. A
  single confirmed mismatch is a kill criterion — brief §12 measure 4.)*

### US-8 · The true count and the capped line

- **AC-24** · *Given* a caller with **150** unread notices of the three kinds, *when*
  `notices_feed(see_all=1)` is called, *then* `unread` is **150** and `items` holds
  **100** rows. *(Today it returns `unread = 100`. The test must fail against today's
  code.)*
- **AC-25** · *Given* the same caller, *then* the return carries **`capped: true`**, and
  the page draws a footer inside the notices group reading **"Showing the first 100
  notices. Older read ones are not kept."**
- **AC-26** · *Given* a caller whose unread grooming notice points at a mark they may no
  longer read (their Employee record is set to `Left`), *then* `unread` **does not count
  it**. *(Oracle: the existing
  `test_a_notice_is_hidden_when_its_reader_may_no_longer_read_the_mark` still passes —
  1 → 0 with no row changed. A plain uncapped `COUNT(*)` fails this.)*
- **AC-27** · *Given* the same site with **20 people** and with **981 people**, *then*
  `notices_feed`'s statement count is **identical**, and that count is **≤ 14**.
  *(Oracle: `test_notices_076.py` — `assertEqual(small.n, big.n)` **unchanged**,
  `assertLessEqual(big.n, …)` raised from 12 to **14**, with the reason in the commit
  message. OPS-28.)*

### US-9 · Mark all as read — and the three assertions that matter

- **AC-28** · *Given* the notices group holds at least one unread notice, *then* a
  **"Mark all as read"** control appears **in that group's heading only**, with a minimum
  height of **44 px on a phone**; *given* nothing is unread, *then* the control is
  **absent** (not greyed).
- **AC-29** · *Given* the page, *then* **no control anywhere on it can mark, clear or
  dismiss a work row.** *(Oracle: a source assertion that the mark-all handler's selector
  cannot match a work row, plus a DOM test asserting group 1 has no such control.)*
- **AC-30** · **(the write, assertion 1)** *Given* the caller has unread notices of all
  three kinds, *when* the bulk mark-as-read is called, *then* **all of the caller's
  notice rows of those three types are `read = 1`**.
- **AC-31** · **(the write, assertion 2)** *Given* the same caller **also** has two
  unread `document_type = "Employee"` notification rows, *when* the call completes,
  *then* **both are still `read = 0`**. *(Drop the `document_type` term and only this
  assertion fails, so the failure names its cause. PPJ's heaviest user carries 406 such
  rows.)*
- **AC-32** · **(the write, assertion 3)** *Given* a colleague has unread notice rows of
  the three kinds, *when* the caller's bulk mark-as-read completes, *then* **every one of
  the colleague's rows is still `read = 0`**. *(Drop the `for_user` term and only this
  assertion fails. **This is the riskiest line in the slice: a wrong write is silent,
  unlogged, and nobody would report it.**)*
- **AC-33** · *Given* the bulk mark-as-read, *then* it is **one** set-based
  `frappe.db.set_value("Notification Log", {for_user: <session user>, read: 0,
  document_type: ["in", NOTICE_DOCTYPES]}, "read", 1)` — **not** a loop over
  `mark_as_read`, and **not** Frappe's `mark_all_as_read`. *(Oracle: a statement-count
  assertion — one write statement for 86 unread rows, not 86.)*
- **AC-34** · *Given* the limit `@_limited(SELF_KEY, "user", limit=30)`, *when* one
  signed-in person calls the bulk mark-as-read **31 times inside the hour**, *then* the
  31st call is **refused** with the server's own sentence, and the counter shows
  `TOO_MANY_TRIES`. **The test proves the refusal by exceeding the limit — never by
  reading the decorator or the docstring.** *(Oracle: the 31st response. **And**: the
  browser sends the call with an **arguments object, even an empty one**, so it is a
  **POST** — `portal.js:15464` sends a no-argument call as a **GET**, and Frappe's
  `rate_limiter.py:133` returns early for any method not in the list, so a GET-shaped
  write would be **unlimited while looking limited**. OPS-22. A second assertion checks
  the request method is POST.)*

### US-10 · Deciding from the page

- **AC-35** · *Given* a leave or expense row in group 1, *when* it is tapped, *then* the
  **existing** `hmLeaveSheet` / `hmExpenseSheet` opens in place, and on a successful
  decision the row leaves, the group heading's number falls by one, **and the badge falls
  by one**.
- **AC-36** · *Given* any other work row, *when* it is tapped, *then* the person is
  navigated through the existing `HM_SCREEN` map and **no write of any kind is sent**.

### US-11 · Failure

- **AC-37** · *Given* `notices_feed` raises and `get_nav_counts` succeeds, *then* group 1
  renders normally, an amber box appears **inside the notices group only** reading
  **"Could not load your notices." / "Your work is shown below. Nothing has been
  lost."** with a **"Try again"** button, **the bell's number is unchanged, and no toast
  appears**.
- **AC-38** · *Given* both calls raise, *then* one amber box is shown reading **"Could
  not load this page." / "Check your connection and try again. Nothing has been lost."**
  with **"Try again"**, no groups are drawn, **and the bell is unchanged**.
- **AC-39** · *Given* one part of `get_nav_counts` raises `PermissionError` (ALV-250's
  shape), *then* the bell is left exactly as it was, no error reaches the screen, and
  the row appears in the Error Log. *(Oracle: a test that makes one part raise.)*

### US-12 · Loading and the empty states

- **AC-40** · *Given* the page is opened, *then* within **300 ms** four grey row-shaped
  bars are drawn with `aria-busy="true"` and the accessible name **"Loading your
  notifications"**, and **a spinner always ends** — it is replaced by rows, an empty box
  or an amber box.
- **AC-41** · *Given* no work, no notices and no own requests, *then* one green tick box
  reads **"Nothing waiting on you, and no new notices." / "Requests that need you,
  notices from HR, and your own open requests all appear here."**
- **AC-42** · *Given* work is empty but notices are not, *then* group 1 shows a tick box
  reading **"Nothing waiting on you." / "Requests that need you, and policies to read,
  appear here."**
- **AC-43** · *Given* notices are empty but work is not, *then* group 2 shows a tick box
  reading **"You have read everything." / "New notices from HR and management appear
  here."**
- **AC-44** · *Given* an employee whose record was created today and who has nothing at
  all, *then* one box reads **"Nothing here yet." / "This is where you will see anything
  waiting on you, and every notice sent to you. We will put a number on the bell when
  something arrives."** *(The empty state is never hidden.)*

### US-4 · The chips

- **AC-13** · *Given* the page opens, *then* three chips are drawn in one row — **"All"**
  (pressed), **"To do"**, **"Unread notices"** — each a real `<button aria-pressed>` in a
  named group, each at least **44 px tall on a phone**, **none ever greyed out**, and
  **no count inside any chip**.
- **AC-14** · *Given* "To do" is pressed, *then* group 1 is shown **whole** (not capped
  at five) and groups 2 and 3 are absent. *Given* "Unread notices" is pressed, *then*
  group 2 is shown whole holding **only unread rows**, its heading reads **"3 unread
  notices"**, and groups 1 and 3 are absent.
- **AC-15** · *Given* any chip is pressed, *then* **no network request is sent** — the
  filter runs over the rows already fetched. *(Oracle: a fetch spy asserts zero calls.
  OPS-5.)*

### US-5 · Five rows per group

- **AC-16** · *Given* "All" and a group holding 86 rows, *then* **five** rows are drawn
  and a footer reads **"Showing 5 of 86"** with a button **"See all 86 notices"**.
- **AC-17** · *Given* that footer button is pressed, *then* it **sets the chip** (no new
  screen, no new address) and the group is shown whole.
- **AC-18** · *Given* a caller with **150** unread notices, *then* the footer's total is
  **150** — the feed's own true count — **never `items.length`**, which would say 100.
- **AC-18a** · *Given* an HR Manager with 63 attendance fixes and `cap = 50`, *then* a
  footer inside group 1 reads **"Showing the first 50 of 63 attendance fixes"**.

### US-13 · Stale rows

- **AC-45** · *Given* a work row whose document somebody else already decided, *when* it
  is tapped, *then* the server refuses, the page shows **"Already decided by someone
  else."**, and the row is removed. **Never a raw server error and never a silent
  no-op.**
- **AC-46** · *Given* a work row whose requester withdrew it, *then* the message is
  **"The request was withdrawn."** and the row is removed.
- **AC-47** · *Given* a row that stopped being the caller's to decide (they no longer
  manage that person), *then* on the next load **the row is absent and nothing at all is
  said about it**. *(Oracle: the DOM contains no message naming the person or the
  change.)*

### US-14 · The CXO

- **AC-48** · *Given* the caller holds System Manager, *then* group 1 shows **one row per
  kind with a count and no colleague names**, tagged "counts by kind", ordered by count
  descending.
- **AC-49** · *Given* the same caller with counts `leave 214, fixes 63, policies 1` and
  `unread = 1`, *then* the badge reads **4** — three kinds plus one unread — not 279.
  *(Oracle: the badge text. A rows badge would read "99+" permanently and never move.)*
- **AC-49a** · *Given* a CXO taps a kind row, *then* that kind's screen opens and **the
  badge does not move** — nothing was decided.

### US-15 · Hindi

- **AC-50** · *Given* the site language is Hindi, *then* every string in §11.1 is drawn
  in Hindi, every one of them passing through `drT()`, and at **390 px** the three chips
  still fit on **one row** with no sideways overflow. *(Devanagari runs ~30% longer —
  Measured by the designer.)*
- **AC-51** · **Not a code test.** *Given* the Hindi strings in §11.1 are a **machine
  draft**, *then* a **native Hindi reader has read and signed off every one of them, by
  name and date, before release.** This is an explicit release item, not an assumption.
  **DECIDED by Surbhi, 6 Nov 2026: any native Hindi reader will do — no particular person
  is required.** The gate itself does not soften: somebody who actually reads Hindi must
  read every string and be recorded by name and date before release. "Any reader" means the
  choice is open, not that the check can be skipped or signed off by a non-reader.

### US-16 · Badge legibility

- **AC-52** · *Given* the desktop badge, *then* its digits are **12 px**, set in
  **`.notif-badge`'s own rule**. *(Oracle: a test that fails if `design_system.html` or
  the `--fs-xs` token is touched by this slice — that file is included by **7** pages.)*
- **AC-53** · *Given* the badge, *then* its background is **`--primary`** and its digits
  **`--on-primary`** — **never red**, never literal white.
- **AC-54** · *Given* the four combinations of theme (light, dark) and brand (Alvora
  purple `#5B4B8A`, PPJ black), *then* the badge's text-on-background contrast is **at
  least 4.5 : 1** in every one. *(The designer measured white on dark `--primary`
  `#A99AD4` at about **2.1 : 1** — a failure. The engineer must also check a pale brand
  seed.)*
- **AC-54a** · *Given* an unread notice row, *then* it is marked by **a dot and** the
  group it sits in — colour is never the only signal — and the badge carries **a number
  and** a spoken name.

### US-17 · must not read a colleague's notice

- **AC-55** · *Given* a **freshly created** site, two users each seeded with unread
  notice rows of the three kinds, and a session as a **plain staff login** (`Employee`,
  `Employee Self Service`, `All`), *then* the colleague's rows are unreachable through
  **all six doors**: the list API with no filter and with a hostile `for_user` filter;
  `reportview.get`; `reportview.get_count` (including with `reference_doctype`);
  `reportview.export_query` (CSV, naming `subject` and `email_content`);
  `client.get` of the colleague's named row (expect `PermissionError`); and
  `has_permission(..., "share", doc=<colleague's row>)` (expect `False`). **The test must
  first assert the colleague's seeded row exists** — otherwise it passes on an empty
  table and proves nothing. *(SEC-5. Slice 028's lesson, and PPJ is exactly where that
  bites today.)*
- **AC-56** · *Given* the new unread count, *when* two users each hold unread notice rows,
  *then* as user A the returned count equals **A's own readable notice rows only** and is
  **strictly less** than the site-wide count of unread rows of those types. *(SEC-1. Plus
  a source assertion that the count's filter dict contains the key `for_user` — because
  `frappe.db.count` applies **no** permission condition and returned **2,016** when asked
  with none. **Delete the `for_user` term and both assertions must fail.**)*
- **AC-56a** · *Given* the new count and the new write, *when* they are called with
  crafted keyword arguments — `document_type=["Employee"]`, `for_user="<colleague>"`,
  `filters={}`, `ignore_permissions=1` — *then* each call is either refused or has **no
  effect on any row outside the caller's three notice types**. *(SEC-3.)*
- **AC-56b** · *Given* the slice's diff, *then* `ignore_permissions` stays at **0** in
  `notices.py` and in any new file (the existing ceiling
  `test_portal_security_010.test_sec16_ignore_permissions_does_not_grow` carries
  `("alvoraa_portal", "notices.py"): 0`), there is **no raw SQL**, and the count of
  `@frappe.whitelist` in `alvoraa_portal` grew by **no more than 1**. *(SEC-4, SEC-3.)*
- **AC-56c** · *Given* an employee whose Employee record is set to **`Left`** while their
  login still works, *when* they call either feed, *then* both return nothing — including
  a `Left` login that still holds **HR Manager**, for whom `hr_scope` must return
  `set()`. *(PRIV-2.)*
- **AC-56d** · *Given* `ROW_KEYS`, *then* `explanation` is **not** in the
  `attendance_fixes` keys and appears in no returned row, and **no** `ROW_KEYS` list
  contains a salary, bank, passport or health fieldname (asserted by name list). *Given*
  `notices_feed`'s return, *then* its key set is **exactly** the set in §6.3 — the
  existing
  `test_the_person_sees_their_own_unread_notice_with_a_fixed_set_of_keys` extended to
  include `capped`. *Given* the slice's diff, *then* it contains **no DocType `.json`**
  and **no Custom Field fixture**. *(PRIV-1, PRIV-2.)*
- **AC-56e** · *Given* the new count and the new write, *then* their return shapes
  contain **no `for_user`, no email, no employee name and no row identifier belonging to
  anybody else** — the count returns a number, the write returns `{"ok": 1}` — and the
  slice's diff adds **no read-receipt field, report or endpoint**. *(PRIV-4.)*

### US-19 · must not mark work owed

- **AC-57** · *Given* any row in group 1 or group 3, *when* it is tapped, *then* **no
  request of any kind is sent on account of the tap** — a decision sheet may later send
  the decision the person makes, but the tap itself writes nothing. *(Oracle: a fetch spy
  asserts zero requests between the tap and the sheet opening.)*
- **AC-58** · *Given* the built portal JavaScript, *then* there is **no code path** that
  sets any "seen", "dismissed", "snoozed" or "done" state on a work row, and the page
  renders **no dismiss, snooze, swipe or X control** on one. *(Oracle: a DOM assertion
  plus a source assertion.)*

### US-20 · must not leave anything on the handset

- **AC-59** · *Given* a full session on the notifications page, *then* **nothing** about
  notices or approvals is written to `localStorage`, `sessionStorage`, IndexedDB or the
  Cache API; `sb-pinned` and the existing theme key remain the **only** client-stored
  keys, and the set of storage call sites has **not grown**. *(SEC-7a, PM-AC-A.)*
- **AC-60** · *Given* a signed-in session, *then* the response for `/hrms-employee`
  carries **`Cache-Control: no-store,no-cache,must-revalidate,max-age=0`**. *(Oracle: the
  header, asserted in CI, so a future edit that drops `context.no_cache` is caught by CI
  and not by a factory floor.)*
- **AC-61** · *Given* the portal service worker, *then* it remains a **no-op** — its
  source contains none of `caches`, `respondWith` or `Cache`. *(SEC-6. A caching service
  worker would hold this page on the handset for ever and no response header would stop
  it.)*
- **AC-62** · *Given* a Guest request to `/hrms-employee`, *then* the response is a
  redirect to **`/alvoraa-login?redirect-to=/hrms-employee`**, and both endpoints throw
  `PermissionError` for Guest. *(SEC-6.)*
- **AC-63** · *Given* a real Android handset, *when* a person signs out at `/logout` and
  presses **Back**, *then* **nothing from the notifications route renders**. **Recorded
  with the Chrome version and the date. This manual check is a release gate.** *(SEC-7b,
  PM-AC-B. See **R5** — if it shows rows, stop; the fallback is one line, clearing the
  rendered rows on `pagehide`, and it is **not specified as work here**.)*
- **AC-63a** · *Given* the route, *then* it is a **fixed word** — `#notifications` — with
  no employee id, document name or email in the URL, the hash, `document.title` or any
  `history.pushState` state. *(PRIV-3: browser history survives sign-out on a shared
  handset and may sync to a personal Google account.)*

### US-21 · must not grow an operational tail

- **AC-64** · *Given* the slice's diff, *then* it contains **no `setInterval`**, no
  `setTimeout` loop and **no polling** of either feed. Refresh stays navigation-triggered
  the way `hmRefreshIfStale` already works. *(OPS-27. A 60-second poll on 441 DTC
  handsets is ≈ **15 extra calls a second, all day**, against roughly zero today.)*
- **AC-65** · *Given* the slice's diff, *then* it adds **no `frappe.enqueue`**, no queue,
  no worker, no `scheduler_events` entry, no alert, no metric, no dashboard and **no
  secret or environment variable**. *(OPS-21, OPS-25, OPS-26.)*
- **AC-66** · *Given* the slice's diff, *then* **`deploy/nginx.conf` is unchanged** and
  **no new web address** is added. *(Oracle: `git diff --stat`. OPS-23. One nginx
  container serves production and dev from that one file.)*
- **AC-67** · *Given* the test suite, *then* `test_notices_076.py`'s flatness assertion
  `assertEqual(small.n, big.n)` is **unchanged**, its ceiling reads **14**, and
  `test_scale_flatness_044.py` and `test_inbox_parts_042.py` need no change. The existing
  front-end CI gates pass: `check_portal_handlers.js`, `check_undefined_js.js`,
  `check_portal_trays.js --static`, `check_design_system.py`, `check_tag_balance.py`,
  `check_brand_spelling.py` and the jsdom DOM tests. *(OPS-28.)*

---

## 10 · Edge cases and boundaries

Only cases that actually happen. Each one names what the person sees.

| # | Case | Expected behaviour |
|---|---|---|
| E-1 | **A new joiner, first morning** — no work, no notices, no requests | AC-44's wording. The page says what it is *for* |
| E-2 | **A leaver whose login still works** (ERPNext does not disable it) | Both feeds return nothing; badge 0. All three scope helpers filter `status = "Active"` — AC-56c |
| E-3 | **A re-hired employee** | Treated as Active again by the same helpers. Notices from the earlier spell are still their own rows, gated by `_readable` |
| E-4 | **An employee with no manager** | Nothing breaks — no approval rows come to them, their own requests show whatever state sentence `get_inbox` already returns |
| E-5 | **A platform operator with no Employee record** | `notices_feed` works (they can hold notices); `get_nav_counts` returns `has_employee: false` and empty parts. No colleague data |
| E-6 | **A manager who stopped managing somebody yesterday** | The grooming review row disappears (`_readable`); the mark notice expired the day after the mark. **Silence** — AC-47 |
| E-7 | **A multi-company HR Manager** | Rows inside `permitted_companies` only. One page, no HR variant |
| E-8 | **A CXO across all companies** | Counts by kind; never names — AC-48, AC-49 |
| E-9 | **The capped notice list** (150 unread) | 100 rows, true count 150, the capped line — AC-24, AC-25, AC-18 |
| E-10 | **The capped work list** (63 attendance fixes, cap 50) | "Showing the first 50 of 63 attendance fixes" — AC-18a |
| E-11 | **A notice whose document was deleted** | `_readable` drops it; the count drops with it; no error — U-14 |
| E-12 | **A work row with no `waiting_since`** | Drawn without the waiting line. **Never "waiting undefined days"** |
| E-13 | **Two managers decide the same request at the same moment** | The second gets the server's own refusal, shown as "Already decided by someone else." — AC-45 |
| E-14 | **The same person clears notices on two devices at once** | The write is idempotent — it sets `read = 1` where `read = 0`. The second call simply matches nothing |
| E-15 | **A grooming notice whose mark is dated today, read by the manager, then read again tomorrow** | Readable today, gone tomorrow (`_readable`: `manager and mark_date == today`). The count moves with it |
| E-16 | **A notice older than 30 days that is still unread** | It stays — unread rows are kept whatever their age (`or_filters` on `notices.py:68`). Only **read** rows fall out of the 30-day window |
| E-17 | **A back-dated announcement** | Ordered by `creation`, not by any effective date. No change from today |
| E-18 | **A row whose amount or date is null** | Drawn without that fragment, never with the word "null" or "undefined" |
| E-19 | **A bulk import that creates hundreds of notification rows at once** | The true count handles it: the gate adds **zero** queries whatever the row count; estimated 10 ms of Python at 5,000 rows |
| E-20 | **Time zone and DST** | The page shows "6 Nov, 4:10 pm" from the site's own time, exactly as `hmWhen` already does. No new date arithmetic, so no new DST surface |
| E-21 | **A cancelled or amended leave application** | The row is simply no longer in the approver's queue; a stale tap gets AC-45's message |
| E-22 | **Half-day and hourly leave** | `half_day` is already in `ROW_KEYS` and reaches the existing decision sheet unchanged. The row line itself is unchanged |
| E-23 | **200% browser text at 360 px** | Chips wrap; nothing is `nowrap`; no fixed minimum widths — AC-13 and the a11y section |
| E-24 | **A shared handset with Hindi and a 99+ badge** | The top bar is full to its edge at 390 px (pre-existing, N6, P4). Accepted; not fixed here |
| E-25 | **An employee with no pending anything, but 86 read notices** | Group 2 shows read rows under "All"; the heading carries no unread tag; "Mark all as read" is **absent** — AC-28 |

**Not an edge case, deliberately:** negative or carry-forward leave balances, holiday
lists, probation, payroll periods. This slice draws rows somebody else computed and
changes none of that arithmetic.

---

## 11 · Notifications, messages and copy

### 11.1 Every user-facing string — exact copy, from the prototype

**This slice sends no email, no SMS, no push and no new notification.** Every string
below is on-screen text. All of it goes through `drT()`. The Hindi column is a **machine
draft** (AC-51).

| Where | English | हिन्दी |
|---|---|---|
| page title, nav item, bell | Notifications | सूचनाएँ |
| bell accessible name | Notifications, {0} waiting | सूचनाएँ, {0} बाकी |
| page sub-line | Last 30 days | पिछले 30 दिन |
| chips | All · To do · Unread notices | सभी · करने के लिए · बिना पढ़ी सूचनाएँ |
| group 1 heading | {0} waiting on you | आप पर {0} बाकी |
| group 2 heading, All / To do | Notices · *tag* {0} unread | सूचनाएँ · {0} बिना पढ़ी |
| group 2 heading, Unread chip | {0} unread notices | {0} बिना पढ़ी सूचनाएँ |
| group 3 heading | Waiting on someone else | किसी और के पास |
| group 3 tag | not counted — nothing for you to do yet | गिनती में नहीं — अभी आपको कुछ नहीं करना |
| notices group action | Mark all as read | सभी को पढ़ा हुआ चिह्नित करें |
| group footer | Showing {0} of {1} | {1} में से {0} दिखाई जा रही हैं |
| group footer button | See all {0} waiting · See all {0} notices | सभी {0} बाकी देखें · सभी {0} सूचनाएँ देखें |
| capped work | Showing the first {0} of {1} attendance fixes | {1} में से पहली {0} हाज़िरी सुधार दिखाई जा रही हैं |
| capped notices | Showing the first 100 notices. Older read ones are not kept. | पहली 100 सूचनाएँ दिखाई जा रही हैं। इससे पुरानी पढ़ी हुई सूचनाएँ नहीं रखी जातीं। |
| empty, everything | Nothing waiting on you, and no new notices. / Requests that need you, notices from HR, and your own open requests all appear here. | आप पर कुछ बाकी नहीं, और कोई नई सूचना नहीं। / जिन अनुरोधों पर आपका फ़ैसला चाहिए, HR की सूचनाएँ, और आपके अपने खुले अनुरोध — सब यहीं दिखते हैं। |
| empty, work only | Nothing waiting on you. / Requests that need you, and policies to read, appear here. | आप पर कुछ बाकी नहीं। / जिन अनुरोधों पर आपका फ़ैसला चाहिए और पढ़ने वाली नीतियाँ यहाँ दिखती हैं। |
| empty, notices only | You have read everything. / New notices from HR and management appear here. | आपने सब पढ़ लिया है। / HR और प्रबंधन की नई सूचनाएँ यहाँ दिखेंगी। |
| first morning | Nothing here yet. / This is where you will see anything waiting on you, and every notice sent to you. We will put a number on the bell when something arrives. | अभी यहाँ कुछ नहीं है। / आप पर जो भी बाकी होगा और आपको भेजी गई हर सूचना यहीं दिखेगी। कुछ आने पर घंटी पर नंबर आ जाएगा। |
| loading | Loading your notifications | आपकी सूचनाएँ आ रही हैं |
| notices failed | Could not load your notices. / Your work is shown below. Nothing has been lost. | आपकी सूचनाएँ नहीं आ पाईं। / आपका काम नीचे दिख रहा है। कुछ भी खोया नहीं है। |
| both failed | Could not load this page. / Check your connection and try again. Nothing has been lost. | यह पेज नहीं खुल पाया। / अपना कनेक्शन देखें और फिर कोशिश करें। कुछ भी खोया नहीं है। |
| retry | Try again | फिर कोशिश करें |
| stale — decided | Already decided by someone else. | इसका फ़ैसला कोई और कर चुका है। |
| stale — withdrawn | The request was withdrawn. | अनुरोध वापस ले लिया गया। |
| row actions | Review · Open | देखें · खोलें |
| Home chip | {0} waiting | {0} बाकी |
| CXO work tag | counts by kind | *needs a native draft* |

**What no message may ever contain:** an absence explanation, a colleague's health,
passport, bank or pay data, a reason for a leave request, who read an announcement, or
the sentence "you no longer approve for Rakesh". **No notification is sent to a peer by
this slice at all**, so there is nothing to leak into one.

### 11.2 The refusal messages that are not ours

The rate-limit refusal and the stale-row refusal are the **server's own sentences**,
reaching the screen through `frappe.throw` → `_server_messages` → the portal's error
handler. The spec does not rewrite them. **A refusal must be a sentence, never a stack
trace and never "check your connection".**

---

## 12 · Non-functional requirements for this slice

Taken from `nfr-budget.md` and the `OPS` items, made specific.

| Dimension | The number for this slice | Source |
|---|---|---|
| Expected record volume | PPJ: **2,016** `Notification Log` rows total, **0** of the three notice kinds, four users over 400 rows of other kinds, heaviest 407 / 406 unread. **DTC (counted 6 Nov 2026, read-only): 948 rows total — `Employee` 902 (all 902 unread), `Alvoraa App Invite` 23, `Report` 22, `Interview` 1, and 0 of all three notice kinds.** Heaviest person 169 rows / 167 unread; three people over 100 unread across all kinds; **483 `Employee Self Service` logins** | PPJ measured by the designer; DTC in `08-dtc-counts.md` |
| Page size for a list | notices `READ_CAP = 100`; work `LIST_CAP = 50` and `CORRECTIONS_CAP = 50` per part; **5 rows per group under "All"** | existing constants |
| Worst-case query | `notices_feed` **≤ 14 statements** (up from ≤ 12) and **identical at 20 people and 981**; `get_nav_counts` **21** statements worst case. The grooming gate adds **zero** queries whatever the row count — longer `IN` lists, not more queries | OPS-13, OPS-28; Measured slice 044, Sep 2026, on fixture sites |
| Response time | **≤ 500 ms p95** per whitelisted call. Worst measured p95 across these calls: **215 ms** (Sep 2026, fixture sites). **Not re-measured in DTC's configuration — OPS-3** | nfr-budget §2 |
| Page weight added | **+8–12 KB gzipped cold** (~2–3% of the asset payload), **~600 B warm** | Estimate, DevOps §2.2 |
| 3G profile | **Chrome DevTools "Fast 3G"** (1.6 Mbit/s, 562 ms RTT), set in the test. **Settled by Surbhi, 6 Nov 2026.** The pre-existing cold-load miss (~621 KB ≈ 3.1 s against 2.5 s) is **accepted in writing on that date and is not this slice's debt** | OPS-16, §3.0 |
| Skeleton | drawn within **300 ms** | nfr-budget §2 |
| Background jobs | **none.** No queue, no worker, no `frappe.enqueue`, no scheduler entry | OPS-21 |
| Polling | **none, ever.** Refresh is navigation-triggered | OPS-27 |
| Rate limits | bulk mark-as-read: **30 per signed-in user per hour**, POST only, `ip_based=False`. **Both reads unlimited** | OPS-22 |
| Cache | **none.** No `call_cache`, no redis, no browser cache of the number | OPS-11, OPS-19 |
| Retention of the data | **unchanged — and unchanged means for ever.** `Notification Log` rows are never deleted; Frappe's `clear_notifications` removes redis keys, not rows. **Pre-existing debt — PRIV-5 / ⚠ DECISION SEC-R1** | OPS-17, counsel 18 Sep 2026 |
| Personal / sensitive data | grooming-mark and grooming-review subjects are **performance records**; announcement subjects are internal; `read` is **behavioural**; approval rows carry colleague personal and financial data, and `lwp_in_play` / `lwp_limit` are pay-adjacent. Protected by the `for_user` pin, the per-part scope, `no-store`, no client storage and no export from this page | 01c §3 |
| Backups | **nothing new to back up.** Every row is an existing `Notification Log` row already inside each site's dump. **ALV-299 (no off-server copy of any backup) is still open and is not this slice's to fix** | OPS-24 |
| Monitoring | watch three things for one week: Error Log rows naming `notices` or `inbox_api`; the existing `TOO_MANY_TRIES` counter; and **one human check that the badge equals the lists on a real tenant**. **No new alert, metric or dashboard** | OPS-25 |
| Rollback | redeploy the previous **`alvoraa-app`** tag with `run_migrations: false`. **The asset stamp must be proved changed by URL** — a hand `docker cp` leaves `assets.json`'s modified time alone and every browser keeps the old JS/CSS for up to 30 days. Budget **8–10 minutes**, not two | OPS-29 |

---

## 13 · Compliance-impact sub-analysis

**I am not a lawyer.** Built on 01c; not re-derived, and nothing here contradicts it.

### 13.1 Data touched

| Field / object | Sensitivity class | Purpose it was collected for | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| `Notification Log.subject` — grooming mark | **sensitive** (performance record, counsel 18 Sep 2026) | tell the person a mark was recorded | employment / legitimate HR administration, as recorded by the employer | **no** |
| `Notification Log.subject` — grooming review | **sensitive** (carries a colleague's name and a red count) | HR and the line manager must know a review is due | same | **no** |
| `Notification Log.subject` + `sender_label` — announcement | **internal** | tell people the rules and the news | same | **no** |
| `Notification Log.read` | **internal / behavioural** | let the person clear their own backlog | same. **Re-using it to tell a sender who read a notice is a different purpose** — refused, §13.4 | **no** |
| Approval row fields (§6.4) | **sensitive** (colleague personal, financial, pay-adjacent) | the named approver is deciding this document | same | **no** |
| `my_requests` fields | **internal** — the caller's own | "where has my request got to?" | same | **no** |
| The rendered page on a shared handset | **sensitive in aggregate** — 30 days of one named person's HR messages in one scroll | — | — | **no, but the exposure shape changes** — §13.3 |

**No statutory-id data anywhere.** No Aadhaar, no PAN, no passport, no bank account.
**Nothing new is collected**, so there is no minimisation case to make.

### 13.2 Obligations engaged

| Obligation | Source | What this slice must do | Feature that does it |
|---|---|---|---|
| Reasonable security safeguards — access control | DPDP Act 2023, baseline §2 (entry dated **24 Aug 2026**) | the record limit sits in Frappe's permission layer, not our page; the two unprotected calls carry explicit `for_user` terms | SEC-1, SEC-2, SEC-5 → AC-30…32, AC-55, AC-56 |
| Purpose limitation | DPDP, same entry | read state stays with the recipient | PRIV-4 → AC-56e; §13.4 |
| Data minimisation | DPDP, same entry | no new field, no new store, no new copy | PRIV-1 → AC-56d |
| Breach intimation — affected people and the Board | DPDP, same entry; counsel 1 Nov 2026 (ALV-249): **a breach counts even with no logged reads** | if the door list ever fails on a real tenant, the clock starts on confirmation | AC-55 is the canary |
| CERT-In — report within 6 hours of awareness | CERT-In Directions, 28 Apr 2022, baseline §3 | nothing new to log. **The 6-hour clock is the binding one if the bulk write ever goes wide** | AC-30…32 |
| Performance records: employment + 6 months, then permanent erasure; indefinite soft-deletion prohibited | **counsel, 18 Sep 2026 — binding** | a grooming-mark notice **is** a performance record, and `Notification Log` rows are kept for ever | **nothing in this slice. Pre-existing. PRIV-5 / ⚠ DECISION SEC-R1.** The purge engine is `compliance-feature-map.md` **A6, not built** |
| Passport and health data are not for managers | counsel, 1 Nov 2026 | none reaches any row | PRIV-2 → AC-56d |
| EU AI Act | baseline §4 | **no surface at all.** No model, no prompt, no automated decision, no profiling | — |
| GDPR | baseline §1 | no EU data subjects in scope for DTC or PPJ | — |

**Housekeeping, not mine to fix but worth saying:** the DPDP and CERT-In baseline entries
are dated 24 Aug 2026 and **go stale on 22 November 2026** (01c R7). Somebody must
re-verify them, and it should not be discovered inside a slice.

### 13.3 Visibility delta

**Entitlement widens by nothing. Exposure shape changes once.**

| Who | Can see after this slice that they could not before |
|---|---|
| Line manager | **their own** work owed, on every screen instead of only Home. Nothing about anyone new |
| HR Manager | nothing new. More rows than others, because their scope was already wider |
| CXO | **less**, arguably — counts by kind rather than 400 names in a payload |
| Employee | their own 30 days of notices on a **durable, addressable, bookmarkable page**, reachable in two taps from any screen. **This is the one change, and it is the compliance event of the slice** |
| Anybody else | **nothing.** Negative cases in §8.2, all ten |
| An outside party | **nothing at all.** No share, no print route, no export from this page |

**The honest downside, in the words we would have to read on a front page:** *"HR portal
adds a notifications page; the previous user of a shared phone could press Back and read
it."* We would not defend that. AC-63 is the gate, and **R5** is the open risk behind it.

### 13.4 Decision automation

**No. Nothing in this slice automates or materially influences a decision about a
person.**

- The page **displays** work that a named human then decides. The accountable human is
  the named approver on the row, or the HR Manager inside their company scope.
- They intervene at the point of decision, in the existing sheet, with a reason box.
- The employee is told the outcome by the existing flow, unchanged.
- They contest it through the existing route, unchanged.
- **No ranking, no scoring, no ordering by anything but age.** Rows are ordered oldest
  `waiting_since` first — a fact, not a judgement.
- **No AI of any kind.** No model, no prompt, no confidence threshold, no cost per use,
  no fallback to specify. §7 of my own template does not apply, and I am saying so rather
  than leaving it blank.

**Prohibitions check:** nothing here sets a rating, infers emotion, voice or face,
monitors behaviour passively, or dresses individual surveillance as transparency. The one
thing that would have — **who read my announcement** — is **refused in writing** by the
named decider (01c §7) and carried as out of scope.

### 13.5 Retention and deletion

| Question | Answer |
|---|---|
| What is kept? | Exactly what is kept today. **This slice creates no new store and no new copy.** |
| For how long? | **For ever.** Nothing trims `Notification Log` — Confirmed: Frappe's `clear_notifications` deletes redis keys, not rows |
| On whose instruction? | Nobody's. It is the absence of a rule, not a rule |
| What survives an erasure request because it is decision-bearing? | A grooming-mark notice records that a performance mark was made. Counsel's 18 Sep 2026 rule is **employment + 6 months, then permanent erasure, and indefinite soft-deletion is prohibited** — so it does **not** survive for ever, and today it does. **That is the gap** |
| Does this slice change any retention clock? | **No.** Written down anyway, as required |
| Who owns the gap? | `hrms-product-manager` to slice it, with counsel's periods already in hand. **⚠ DECISION SEC-R1 — Surbhi to accept it in writing, with a date.** It changes no line of this slice |

### 13.6 ⚠ Open compliance questions

| Question | Who must decide | What it blocks |
|---|---|---|
| **⚠ DECISION SEC-R1** — do you accept, in writing and with a date, that `Notification Log` rows (including grooming-mark notices, which counsel classes as performance records) are kept for ever, as pre-existing debt this slice does not fix? | **Surbhi** | Nothing in this slice. It is the difference between an accepted risk with a name and a date, and an unnamed one waiting for an owner |
| **⚠ COMPLIANCE / PM-9** — may an employer show an announcement sender which named employees have and have not opened an internal notice, and if so on what lawful basis and with what notice? | `hrms-security-privacy-engineer` has ruled **no** for now; **Surbhi, with counsel**, if she wants it | Nothing here. Its own slice |
| Who is the **named compliance owner**? `product-context.md` §5 still says `TODO — founder to name a person` | **Founder** | Who signs the question above, and who owns a DPDP notice if AC-63 ever fails in the field. I have had to write "Surbhi, with counsel" throughout |

**Flagged, not ruled.** None of these is a legal finding of mine.

---

## 14 · Audit and traceability

| What must be reconstructable | How, today | Verdict |
|---|---|---|
| Who marked a notice read, and when | `Notification Log.modified` and `modified_by` are set by Frappe's own `mark_as_read`. **The bulk write uses `update_modified=False`** (OPS-15's shape), so it deliberately does **not** stamp `modified` — that is what keeps it one cheap statement | **Accepted gap, named.** A year later you could not prove *when* a bulk clear happened. The data is not decision-bearing — nobody's pay or rating turns on when a notice was read — so I am not asking for an audit field. **⚠ If Surbhi wants it auditable, say so: it is a different shape and costs a statement per row** |
| Who approved a leave or claim from this page | the existing approval document's own trail, unchanged | **Already there.** The decision is recorded on the document, which is where an auditor would look |
| Which screen raised a decision | **nowhere.** There is no field for it, and adding one is refused — G-14 | Measure 1 of the brief is dropped rather than a field added |
| A read leak of `Notification Log` | **nothing logs list reads.** There is no audit ledger (`compliance-feature-map.md` A2, status `?`) | **Pre-existing detection gap, named in 01c §1.** Not this slice's to build. It is why AC-30…32 and AC-55 must be written to **fail** when the control is removed |
| That no bypass was added | the CI ceiling on `ignore_permissions` and the whitelist count — AC-56b | **Already there** |

**Nothing in this slice writes to an Error Log, a log line or a job argument that
contains personal data** — the new code is a `COUNT` and an `UPDATE`, and neither handles
a name or a subject.

---

## 15 · Data migration and backfill

**Nothing.**

- No DocType, no field, no Custom Field, no property setter, no table, no index.
- No `patches.txt` entry and no patch. **A migration dry run of nothing is theatre**
  (OPS §3.11) — if the engineer's strategy adds a patch, this comes straight back as a
  P1 at the strategy gate.
- No record needs creating, defaulting or recomputing on any existing tenant.
- No seeding on a real tenant. **Demo seeding on the local bench is a separate need**
  (PPJ holds zero rows of the three kinds), and it is Surbhi's call, not part of this
  slice.
- **Rollback:** redeploy the previous `alvoraa-app` tag with `run_migrations: false`,
  then prove the asset stamp changed **by URL** — OPS-29.

---

## 16 · Localisation and accessibility

| Item | Requirement |
|---|---|
| Translatable strings | **every** string in §11.1, through `drT()`, which already wraps this block |
| Hindi | at parity, ~25 strings. **A machine draft needs a native reader before release — AC-51, ⚠ DECISION BA-3.** One string ("counts by kind") has no draft at all |
| Devanagari length | runs ~30% longer. Measured: the three chips still fit on one 390 px row |
| Dates, numbers, money | unchanged — `hmWhen`, `hmRange`, `fmtMoney` already format them. "6 Nov", no year |
| Text floor | **12 px everywhere.** The badge's 12 px is set in `.notif-badge`'s own rule; `--fs-xs` is **not** touched — `design_system.html` is included by 7 pages (AC-52) |
| Contrast | 4.5 : 1 for the badge in all four theme × brand combinations, with its own foreground token (AC-54) |
| Colour never the only signal | an unread notice carries a **dot and** its group; the badge carries a **number and** a spoken name (AC-54a) |
| Targets | phone: chips 44 px, rows 64 px, bell 44 px, **"Mark all as read" 44 px minimum height**. Desktop: bell 36 px, nav item 38 px, rows 60 px |
| Keyboard | chips are `<button aria-pressed>` in a named group; rows are `<button>`; the new nav item is a `<button>`. Focus is a 3 px `--primary` outline |
| Screen reader | the bell is named "Notifications, 7 waiting"; loading is `aria-busy` **with a name**, not a bare spinner; group headings are real `<h2>` |
| 200% text | chips wrap; nothing `nowrap`; no fixed minimum widths. **Still to test on a real build** |
| No focus trap | the page replaces an overlay, so there is no trap, no Escape handling and no "return focus to the opener" to get wrong |
| The shift / frontline worker without a laptop | **This is the primary hard case.** On a 390 px phone they get the existing 44 px bell, the same page with work first, three chips in one row, no fourth bottom-bar item, and **nothing cached** — 441 DTC logins share these handsets |

---

## 17 · Risks carried, not solved

| # | Risk | What I am asking for | Owner |
|---|---|---|---|
| **SEC-R1** | **`Notification Log` rows are never deleted, and a grooming-mark notice is a performance record under counsel's binding 18 Sep 2026 rule** (employment + 6 months, then permanent erasure; indefinite soft-deletion prohibited). The purge engine (A6) is not built | **Pre-existing debt, its own slice.** **ACCEPTED IN WRITING by Surbhi on 6 Nov 2026**, scoped to slice 083 only — not a standing waiver, and it does not carry to a later slice that adds a new store of performance data. It changed no line of this slice | **Closed.** `hrms-product-manager` still to slice the purge engine (A6) |
| **R5** | **Chrome Android's back/forward-cache behaviour for a `no-store` page is unproven.** If it restores the page instead of evicting on the `sid` change, the next holder of a shared handset sees the previous holder's 30 days of HR messages | **A release gate: one check on one real handset** (AC-63), recorded with the Chrome version and date. The fallback is named — clear the rendered rows on `pagehide` — and is **deliberately not specified as work**, because writing a control before knowing it is needed is what `no-over-engineering.md` forbids | `hrms-test-automation-engineer` to run; **Surbhi** if it fails |
| **R6 / OPS-3** | **Nobody has counted notification rows or roles at DTC, and PPJ holds *zero* rows of the three kinds the bell shows.** So **every control in this slice is currently unobservable on real data**, and "0 findings" from any run on PPJ today means nothing | **CLOSED 6 Nov 2026 — the count was authorised and run, read-only. See `08-dtc-counts.md`.** The kill criterion did **not** fire: DTC holds **0** rows of all three notice kinds, so nobody is near the 100-row cap and the page shape stands. Two findings replace the risk: DTC carries **902 unread `Employee`** rows, which raises AC-31 from a precaution to the spec's most important assertion; and the notices half of the bell is **empty at DTC on day one** — a product fact for DTC, not a defect. Still untested on real notice data, because no such data exists anywhere yet | **Closed** |
| R2 | An employee can CSV-export their own notice bodies from the Desk and have it emailed to their own address | **Accepted** by the security engineer, 6 Nov 2026 — own data, own address; DPDP treats self-access as a right | closed |
| R3 | Role `All` holds `share` on `Notification Log`, and a `DocShare` overrides our `has_permission` hook for the single-document door, so a person can disclose **their own** notice row | **Accepted, P4, reversible** — one `Custom DocPerm` if it ever matters. Nobody can share anyone else's row (Verified) | closed |
| R4 | `inbox_api.py` holds one `ignore_permissions` and has **no** CI ceiling, so a second could land unnoticed | **Not this slice's file.** Routed | `hrms-security-privacy-engineer` |
| R7 | The DPDP and CERT-In baseline entries go stale **22 November 2026** | Re-verify before then, not inside a slice | `hrms-security-privacy-engineer` |
| R8 | **Every demo login on the local bench lands on "Set Password"** (ALV-232 lock), and PPJ has no data of these kinds — so this page cannot be reviewed in a browser as an employee | OPS-20's one write, **held awaiting Surbhi**. Plus demo seeding, which is a separate decision | **Surbhi** |

---

## 18 · Traceability

Every brief line, every prototype screen and state, and every `SEC`, `PRIV` and `OPS`
item. A row with no AC is a **gap** and is marked as one.

### 18.1 Brief → story → AC

| Source | ID or line | Story | ACs | Status |
|---|---|---|---|---|
| Brief | "notifications bell icon on the employee self service portal as well" | US-1 | AC-1, 2, 3 | covered |
| Brief | "redirect to a page which shows all notifications" | US-2, US-3 | AC-4…10 | covered |
| Brief | "with a few filters" | US-4 | AC-13, 14, 15 | covered |
| Brief §5.2 | a real page with an address and a sidebar entry | US-2 | AC-4, 5, 6 | covered |
| Brief §5.4 | "Mark all as read", notices group only | US-9 | AC-28, 29 | covered |
| Brief §5.5 | say when the list was cut | US-8, US-5 | AC-25, 18, 18a | covered |
| Brief §5.6 | "Waiting on someone else" as a third, uncounted group | US-3 | AC-8, 10, 19 | covered |
| Brief §5.7 | say "Last 30 days" | US-3 | AC-7 | covered |
| Brief §5.9 | Hindi at parity | US-15 | AC-50, 51 | covered |
| Brief §5.10 | approvals in the bell from any screen | US-6 | AC-11, 19 | covered |
| Brief §5.11 | approve and decline on the page, reusing the sheets | US-10 | AC-35, 36 | covered |
| Brief §5.12 / PM-4 / UX-3 | CXO badge counts kinds | US-14 | AC-48, 49, 49a | covered |
| Brief §5.13 | one page, no HR variant | US-5 | AC-16, 18a | covered |
| Brief §6 (the WOW) | badge 7 → 5 as two are approved, and you can see which part moved | US-10, US-6 | AC-35, AC-19 | covered |
| Brief §8.2 / PM-2 | badge excludes own requests; **Home's chip changes to match** | US-6, US-7 | AC-11, 21, 22, 23 | covered |
| Brief §8.3 r1 | tapping a task navigates and marks nothing, ever | US-19 | AC-57, 58 | covered |
| Brief §8.3 r2 | a task leaves for three reasons; a stale tap says which; a scope change says nothing | US-13 | AC-45, 46, 47 | covered |
| Brief §8.3 r3 | nothing about notices is cached in the browser | US-20 | AC-59, 60 | covered |
| Brief PM-1 | two counted groups plus one uncounted | US-3 | AC-8, 19 | covered |
| Brief PM-3 | browser-side filters over the existing window; three chips | US-4 | AC-15, 13 | covered |
| Brief PM-5 / UX-4 | badge colour `--primary` | US-16 | AC-53, 54 | covered |
| Brief PM-6 | bell in Frappe's navbar, right of the avatar | US-1 | AC-1 | covered |
| Brief PM-7 | hash route, not a new web page | US-21 | AC-66 | covered |
| Brief §7 pile 2 | the 12 px badge floor | US-16 | AC-52 | covered |
| Brief §9 PM-AC-A | nothing in local/sessionStorage | US-20 | AC-59 | covered |
| Brief §9 PM-AC-B | Back after `/logout` renders nothing | US-20 | AC-63 | covered |
| Brief §12 measure 1 | share of approvals decided from the new surface | — | — | **DROPPED — needs a new field. ⚠ DECISION BA-1**, per the brief's own instruction |
| Brief §12 measure 2 | median days an approval waits | — | — | not an AC — a one-off report over `waiting_since`, after release |
| Brief §12 measure 3 | unread notices older than 14 days | — | — | not an AC — a read-only count, after release |
| Brief §12 measure 4 | the badge equals its lists, zero defects | US-6, US-7 | AC-19, 20, 23 | covered |
| Brief PM-8 | the five stale sidebar badges | — | — | **not adopted — Surbhi's decision, separate slice** |
| Brief PM-9 | may a sender see who read their notice | — | — | **not adopted — out of scope, security engineer ruled no; Surbhi with counsel** |
| Design N1 / UX-5 | the capped unread count | US-8 | AC-24, 25, 26 | covered |
| Design N2 | five rows per group under All | US-5 | AC-16, 17, 18 | covered |
| Design N3 | the badge needs its own foreground token | US-16 | AC-54 | covered |
| Design N4 / UX-1 | "Notices · 3 unread" under All | US-3 | AC-8 | covered — **⚠ DECISION UX-1**, one string |
| Design NB2 | one paint function, three call sites | US-6 | AC-12 | covered |
| Design N5 | the new nav item is a real `<button>` | US-2 | AC-6 | covered |
| Design NC1 | `capped` on the return | US-8 | AC-25 | covered |
| Design N6 | Hindi + 99+ fills the 390 px bar | — | — | **not adopted** — pre-existing, P4, recorded in E-24 |
| Design NX1 | the five stale badges | — | — | **not adopted** — out of slice |
| Design NX3 / UX-7 | every demo login lands on Set Password | — | — | **not adopted** — R8, OPS-20, held for Surbhi |

### 18.2 Prototype screens and states → AC

| Prototype | AC |
|---|---|
| Screen: **Notifications page** | AC-7, 8, 9, 10 |
| Screen: **Home — the changed card** | AC-21, 22, 23 |
| Width: **desktop 1180 px** | AC-1, 2, 4 |
| Width: **phone 390 px** | AC-13, 28, 50 |
| Theme: **light** / **dark** | AC-54 |
| Brand: **Alvora purple** / **PPJ black** | AC-54 |
| Language: **English** / **हिन्दी** | AC-50, 51 |
| Person: **line manager, Sakshi Verma** | AC-11, 19, 35 |
| Person: **employee, Rakesh Kumar** | AC-10, 22 |
| Person: **HR Manager, a busy inbox (capped)** | AC-16, 18, 18a, 24, 25 |
| Person: **CXO, counts by kind** | AC-48, 49, 49a |
| Person: **new joiner, first morning** | AC-44 |
| State: **Loaded** | AC-8, 9 |
| State: **Loading** | AC-40 |
| State: **Notices failed, work loaded** | AC-37 |
| State: **Both calls failed** | AC-38 |
| State: **Stale row — already decided** | AC-45 |
| State: **After approving two** | AC-35, AC-19 |
| Behaviour: **chips** | AC-13, 14, 15 |
| Behaviour: **marking a notice read** | AC-28 (and G-9: Frappe's own single-row call) |
| Behaviour: **Mark all as read** | AC-29…34 |
| Behaviour: **tapping a work row** | AC-35, 36, 57, 58 |
| Behaviour: **tapping a CXO kind row** | AC-49a |
| Line: **"Showing 5 of 86" + "See all 86 notices"** | AC-16, 17, 18 |
| Line: **capped work footer** | AC-18a |
| Line: **capped notices footer** | AC-25 |
| Empty: **everything** / **work only** / **notices only** / **first morning** | AC-41, 42, 43, 44 |
| Tag: **"not counted — nothing for you to do yet"** | AC-8 |
| Tag: **Sample** on every invented row | not built — scaffolding (P-7) |
| Review bar and yellow arithmetic line | not built — scaffolding (P-7) |

### 18.3 SEC and PRIV → AC

| Requirement | AC | Status |
|---|---|---|
| SEC-1 · the true unread count's `for_user` filter is a tested contract | AC-56 | covered |
| SEC-2 · the bulk write is bounded to the caller **and** the three types | **AC-30, AC-31, AC-32** (three separate assertions), AC-33 | covered |
| SEC-3 · no client-supplied filter, doctype, field or user; at most +1 whitelist | AC-56a, AC-56b | covered |
| SEC-4 · no bypass added | AC-56b | covered |
| SEC-5 · the Frappe door list becomes a test, on a fresh site, with the colleague's row asserted to exist | AC-55 | covered |
| SEC-6 · behind the session, at no new address, service worker a no-op | AC-60, AC-61, AC-62, AC-66 | covered |
| SEC-7 · the handset leaves nothing — (a) no client storage, (b) Back after logout | AC-59, AC-63 | covered; **(b) is a manual release gate — R5** |
| PRIV-1 · the field set is frozen and proved | AC-56d | covered |
| PRIV-2 · no absence explanation, health, passport, bank, pay or salary; a leaver reaches nothing | AC-56c, AC-56d, §6.4 | covered |
| PRIV-3 · the route and page carry no identifier | AC-63a | covered |
| PRIV-4 · read state stays with the recipient | AC-56e | covered |
| PRIV-5 · the retention answer is written down and the gap routed | §13.5, **⚠ DECISION SEC-R1** | **not a test, by design — a sentence and a ticket** |

### 18.4 OPS → AC

| OPS | AC or disposition |
|---|---|
| OPS-1 · the bell takes `get_nav_counts`, never `get_inbox` | AC-11 (the badge is summed from `parts[]` counts); §1 |
| OPS-2 · where the two numbers are added | **in the browser** — AC-11, AC-15 |
| OPS-3 · measure `get_nav_counts` on a DTC-shaped copy before part 3 ships | **R6 — a kill criterion, not an AC.** Nobody has the number |
| OPS-4 · hash route, no nginx change | AC-66 |
| OPS-5 · filters over the rows already fetched | AC-15 (settled; §3.0 of DevOps) |
| OPS-6 · both calls fail silently, badge unchanged, no toast | AC-37, AC-38, AC-39 |
| OPS-7 · put the DTC leave-row branch under the flatness test | **not adopted — pre-existing, out of slice.** Recorded |
| OPS-8 · the two doctype sets stay disjoint | AC-20 |
| OPS-9 · no client-supplied filter selecting a doctype, field or user | AC-56a (DevOps' own correction: the write **is** a new whitelisted endpoint, and it takes nothing from the client) |
| OPS-10 / OPS-18 · the door list as a plain staff login on a fresh site | AC-55 |
| OPS-11 · no cache of the badge | AC-64 (no timer), §12; no cache key is introduced |
| OPS-12 · nothing new to deploy or monitor | AC-65 |
| OPS-13 · the true count as two statements split by kind | AC-24, AC-26, AC-27 |
| OPS-14 / OPS-27 · no polling, ever | AC-64 |
| OPS-15 · one set-based UPDATE, not a loop, not Frappe's `mark_all_as_read` | AC-33, AC-31 |
| OPS-16 · the 3G profile is Fast 3G; the cold-load miss is accepted | §12. **Settled by Surbhi, 6 Nov 2026** |
| OPS-17 · nothing trims Notification Log; retention is a separate decision | §13.5, **⚠ DECISION SEC-R1** |
| OPS-19 · assert the header that is already there; test Back on a real handset | AC-60, AC-63 |
| OPS-20 · the demo-login write on the local bench | **held awaiting Surbhi — R8.** Not an AC |
| OPS-21 · no queue, worker, scheduled job or `enqueue` | AC-65 |
| OPS-22 · rate-limit the write at 30/user/hour, POST, proved by exceeding the limit | **AC-34** |
| OPS-23 · hash route; `deploy/nginx.conf` not edited | AC-66 |
| OPS-24 · nothing new to back up; ALV-299 still open | §12, §15 |
| OPS-25 · watch three things; add no alert | AC-65, §12 |
| OPS-26 · no secret | AC-65 |
| OPS-28 · ceiling 14, flatness untouched, existing CI gates pass | AC-27, AC-67 |
| OPS-29 · what "rolled back" means | §12. A release-plan item, not an AC |
| OPS-30 · the deploy sequence | §12 and the release plan. Not an AC — it is Surbhi's gate sequence |

**Gaps, listed honestly:** OPS-3 and OPS-7 have no AC. OPS-3 is **R6**, a kill criterion
nobody can close from a desk. OPS-7 is pre-existing and out of slice. Brief measure 1 is
**dropped** on the brief's own instruction (⚠ DECISION BA-1). SEC-7(b) and AC-51 are
**manual** gates, not automated tests, and are named as such rather than hidden.

---

## 19 · Subtract pass

I read this spec again asking only *what can I delete and still meet the requirement?*
**Removed:**

- **A workflow state table for notices** with states `new → delivered → read → archived`.
  Only `read` exists and only two values of it. The table now has two rows and says so.
- **An "audit field" requirement** on the bulk write (`last_bulk_cleared_on`). It is a new
  field for a behaviour nobody needs to reconstruct, and §14 says so plainly instead.
- **Four edge cases I had drafted** — leave-balance arithmetic, holiday lists, probation
  and payroll periods. This slice draws rows somebody else computed. An AC nobody can
  trigger is scope smuggled in.
- **A story for "a fourth chip for read notices"** and a story for **per-chip counts**.
  Both are refused in 01a §6 and 01b §14 and neither traces to the brief.
- **A story for the five stale sidebar badges.** Surbhi's decision, separate slice.
- **A `pagehide` row-clearing requirement.** It is the right fix *if* AC-63 fails. Named
  as the fallback in R5 instead, exactly as the security engineer asked.
- **A composite index requirement** on `(for_user, read, document_type)`. No measured
  number misses the budget. The shape is named in DevOps §2.1 for whoever ever has it.
- **A per-door acceptance criterion** (ten ACs, one per row of `data-doors.md`). Collapsed
  into AC-55, six assertions in one test. A long list buries the two that matter.
- **Success measure 1** from the brief, and I said why rather than quietly leaving it in
  the traceability table as "covered" — G-14, ⚠ DECISION BA-1.
- **A "notification preferences" story** that had crept back in from the competitor table.
  It is BambooHR's per-category switch wearing different words, refused in the brief §3.

**Kept despite the pass, each with a reason:** the three separate write assertions
(AC-30, 31, 32) — one combined AC would not name the cause of a failure, and this is the
line where a failure is silent; the full `ROW_KEYS` parity table (§6.4) — the security
engineer asked for it explicitly, and the design's summary is genuinely shorter than the
code; the ten negative permission sentences (§8.2) — in an HR system the permission
matrix **is** the feature; and the three carried risks (§17), because an unnamed accepted
risk is the thing this section exists to prevent.

---

## 20 · Open questions

| # | Decision | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| **SEC-R1 — ANSWERED 6 Nov 2026** | Accept in writing, with a date, that `Notification Log` rows — including grooming-mark notices, which counsel classes as performance records — are kept **for ever**, as pre-existing debt this slice does not fix | **Surbhi** | — | **Accepted**, dated 6 Nov 2026, scoped to this slice only. The purge engine (A6) still needs its own slice from the PM |
| **R6 / OPS-3 — ANSWERED 6 Nov 2026** | Authorise a **read-only count on DTC** — roles per staff login, User Permission rows, and `Notification Log` rows by `for_user` and `document_type` | **Surbhi** | — | **Authorised and run** the same day. Results in `08-dtc-counts.md`. Kill criterion did not fire; the page shape stands |
| **⚠ DECISION UX-1** | Under "All", does the notices heading read **"Notices · 3 unread"** (the designer's named divergence) or the brief's **"3 unread notices"**? | **Surbhi** | One string | The designer's version. A heading must name its own list, and the brief's words survive under the Unread chip |
| **⚠ DECISION BA-1** | Drop brief §12 success **measure 1** ("share of approvals decided from the notifications page")? It needs a new field, and the brief itself says to drop it rather than add one | **Surbhi** | One success measure, nothing in the build | Drop it. Measures 2, 3 and 4 need no new storage and still answer "did this work?" |
| **⚠ DECISION BA-2** | The new sidebar item carries **the word "Notifications"**, while the live rail is icon-only with no labels. Is the new item allowed to be the only labelled one? | **Surbhi** | One nav item's appearance | Yes — and note that labelling the whole rail is a real improvement for a separate slice. An unlabelled item cannot be found, and `mayOpenPanel` needs it visible |
| **⚠ DECISION BA-3** | Name the **native Hindi reader** who signs off the ~25 machine-drafted strings before release (one, "counts by kind", has no draft at all) | **Surbhi** | Release, not build | Name a person. This is an explicit item, not an assumption |
| ⚠ R5 | Who runs the **one Android handset check** (Back after `/logout`), and when? | `hrms-test-automation-engineer`; **Surbhi** if it fails | **Release.** If it shows rows, stop — the fallback is one line | Before release, recorded with the Chrome version and date |
| ⚠ OPS-20 / R8 | Set `last_password_reset_date` on **one** named demo employee on the local bench, and seed demo notice rows, so this page can be reviewed in a browser as an employee | **Surbhi** | Nothing in this slice — but it costs every future slice an hour | Approve the one write, on the local bench only, and record which account |
| ⚠ COMPLIANCE / PM-9 | May an announcement sender see **who read** their notice? | `hrms-security-privacy-engineer` has ruled **no**; **Surbhi with counsel** if she wants it | Nothing here | Out of scope. Its own slice. The aggregate version ("Sent to 441 · read by 318") is the only shape worth discussing, with a minimum-audience floor and no drill-down |
| Blocked by a `TODO` | Who is the **named compliance owner** (`product-context.md` §5)? | **Founder** | Who signs PM-9, and who owns a DPDP notice if AC-63 ever fails | Name a person, not a function |
| Nice to know | Do DTC's staff logins carry any User Permission on a **`User`** record (as opposed to PPJ's `Employee`-only rows)? | `hrms-devops-engineer`, read-only | Nothing. It would change 01c §2's share answer, not any control | Answered for free by R6's count |

---

## 21 · Assumptions

- `[ASSUMPTION]` Reusing `hmLeaveSheet` / `hmExpenseSheet` on the new page is clean. **If
  it is not, drop approve-from-the-page to "later" rather than writing a second sheet** —
  US-10 is the only story that falls, and nothing else depends on it.
- `[ASSUMPTION]` A bell fits in Frappe's website navbar without fighting the template.
  **Strongly supported by measurement** — the bar is 1440 × 50 px and holds one 60 px
  avatar. The engineer confirms feasibility (PM-6).
- `[ASSUMPTION]` Both calls answer inside the ≤ 500 ms p95 budget at DTC's ~600 staff.
  The only measurements are slice 044's, September 2026, on fixture sites with no pay rule
  set enabled. **OPS-3 / R6 closes it.**
- `[ASSUMPTION]` A typical DTC employee carries single-digit unread notices. **Unverified
  — PPJ carries zero of the relevant kinds, which proves nothing.** The page is drawn for
  the hundreds case either way (five rows per group, the capped lines, the true count).
- `[ASSUMPTION]` The signed-in page's `Cache-Control` really is `no-store`. The security
  engineer observed the header on a real **Guest redirect** and traced the same
  `setdefault` path for the signed-in page. **AC-60 turns the inference into a CI
  assertion.**
- `[ASSUMPTION]` `frappe.db.set_value` accepts an `["in", [...]]` filter for the bulk
  write. **The security engineer verified this by running it** against a filter matching
  nothing, then rolled back. Labelled as an assumption only because I did not run it
  myself.
- `[ASSUMPTION]` Nothing in this slice touches the phone app, because mobile is a PWA
  over the same portal (Surbhi, 24 Oct 2026). **No mobile artifact, no mobile engineer.**
- `[ASSUMPTION]` DTC is the only tenant where this matters in the first six weeks.
- **Nothing in this spec was seen in a browser.** The design's measurements are the
  designer's, taken on the local bench on 6 Nov 2026; every code claim labelled
  **Confirmed** I read in the source in this worktree at `814d540f`; everything else is
  labelled.

---

## 22 · Ready check — Definition of Ready

**The Definition of Ready passes. Six boxes are ticked with a condition attached, and I
name each one rather than smoothing it over.**

**The brief**

- [x] One named user, one complete outcome — the employee, "is anything waiting for me".
- [x] The job is in Surbhi's own words, dated and quoted.
- [x] Competitive analysis across six whole products, every claim labelled, including
      what we will not copy.
- [x] Kano class stated and marked **proxy**, with the demand evidence.
- [x] Every idea from the opportunities scan decided — 18 rows, in / later / no, each with
      a reason.
- [x] The WOW is named, specific, and achievable in this slice (the sheets already
      decrement the count).
- [x] Out of scope written down explicitly.
- [x] **Surbhi approved the brief, 6 Nov 2026.**

**The design**

- [x] A clickable prototype exists at
      `C:/Surbhi-Git/hrlocal-data/prototypes/083-ess-notifications/prototype-v1.html` —
      five people, six states, two widths, two themes, two brands, two languages — and
      **Surbhi approved the design, 6 Nov 2026.**
- [x] Feedback logged in `.claude/context/ux-learnings.md` *(modified in this worktree;
      the designer owns it).*
- [x] Every state designed: loading, both failures, five empty states, stale rows, capped
      lists, no-permission (does not arise), signed-out-then-Back.

**The requirements**

- [x] `01c` written, **SEC-1…SEC-7 and PRIV-1…PRIV-5**, each with how it is tested.
- [x] `07` §1–§3 written, **OPS-1…OPS-30**.
- [x] Gap analysis done against the **actual source**, verified in this worktree — 17 rows,
      five of them **Drop**.
- [x] Epic and 21 stories, named personas, INVEST-checked, sized (48 points, no 8), linked
      to prototype screens, **including five "must not" stories**.
- [x] Every story has at least one Given/When/Then AC with an observable oracle.
- [x] **Traceability complete** — §18, four tables. Three items carry no AC and **each is
      named as a gap with its reason**: OPS-3 (= R6, a kill criterion), OPS-7
      (pre-existing, out of slice), and brief measure 1 (**dropped on the brief's own
      instruction**, ⚠ DECISION BA-1).
- [x] Permission matrix written, **including ten explicit negative cases**, with the
      Frappe door named per rule and its verification status.
- [x] Edge cases listed — 25 of them, including leavers, re-hires, mid-flow manager
      changes, concurrency, capped lists, bulk imports, time zones and multi-company.
- [x] NFR numbers pulled from the budget and made specific — §12.
- [x] Migration stated: **none**, and why a dry run would be theatre.
- [x] Compliance-impact sub-analysis present — all six parts, plus the AI section marked
      **not applicable and said so**.
- [x] Every ⚠ COMPLIANCE question names a human and what it blocks.
- [x] Nothing requires a prohibited capability. **No AI surface at all.** The one
      surveillance-shaped request — who read my announcement — is **refused in writing**.
- [x] `new-frappe-app-checklist.md` — **not applicable**, this slice installs no app.
- [x] Open questions have owners, and **none blocks the first day of work.**

**The six conditions, stated plainly so nobody discovers them later:**

1. **SEC-R1 — CLOSED 6 Nov 2026.** Surbhi accepted the for-ever retention of notification
   rows in writing, dated, scoped to this slice only and explicitly not a standing waiver.
   Recorded in `01c-security-privacy-requirements.md`, risk R1. It changed no line of code.
2. **R6 — CLOSED 6 Nov 2026.** Surbhi authorised the read-only count; it was run against
   `dtc.alvoraa.co` the same day. **Results in `08-dtc-counts.md`.** The kill criterion did
   not fire: DTC holds **zero** rows of all three notice kinds, so nobody is near the
   100-row cap and the page shape stands. The count found two things instead — DTC carries
   **902 unread `Employee` notification rows** (PPJ's heaviest user has 406), which makes
   AC-31 the most important assertion in the spec; and the notices half of the bell will be
   **visibly empty at DTC on day one**, which is a product fact to tell DTC, not a defect.
3. **R5 is a release gate** — one Android handset, Back after logout, recorded.
4. **AC-51 is a release gate** — a native Hindi reader, named.
5. **UX-1, BA-2 and BA-3 — all decided by Surbhi on 6 Nov 2026.** UX-1: the heading reads
   **"Notices · 3 unread"**. BA-2: the new sidebar item **may be the only labelled one**.
   BA-3: **any** native Hindi reader, with the sign-off itself still required by name and
   date. **BA-1 remains the analyst's recommendation** — drop the brief's success measure 1,
   because measuring it needs a new field and the brief itself says drop rather than add.
6. **The page cannot be reviewed in a browser as an employee today** (R8 / OPS-20).
   That is a review problem, not a build blocker.

---

**Written by `hrms-business-analyst`, 6 November 2026. I recommend; Surbhi decides. I am
not a lawyer, and every point of law above is counsel's ruling with its date or a
question marked for them.**
