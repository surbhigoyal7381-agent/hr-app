---
slice: 083-ess-notifications
artifact: 01b-ux-design
author: hrms-ux-designer
date: 2026-11-06
status: draft — for Surbhi at the design gate
inputs: [01-product-brief.md, 01a-ux-opportunities.md, 07-devops-inputs.md §1, .claude/context/ux-learnings.md, .claude/context/data-doors.md, .claude/context/no-over-engineering.md, .claude/context/nfr-budget.md, .claude/context/product-context.md, .claude/context/handoff-contract.md, design_system.html, frame.html, frame.css, panels.css, portal.js, notices.py, inbox_api.py, auth.py, the running bench hrlocal-bench / ppj.localhost]
---

# 083 · A notifications bell and page — UX design

**Prototype:** `C:/Surbhi-Git/hrlocal-data/prototypes/083-ess-notifications/prototype-v1.html`
**I could not publish it** — no artifact tool in this run. The session that ran me must
publish it and put the link in front of Surbhi. It opens as a plain file in a browser.

**Screenshots (tenant data — outside the repo):**
`C:/Surbhi-Git/hrlocal-data/ux-review/2026-11-06/`

---

## Bad news first, four things

1. **I found a counting fault that is bigger than anything in the scan, and it is in the
   number Surbhi just approved.** `notices_feed` computes `unread` from a list it has
   already capped at 100 rows (`notices.py:68–75`, **read today**). So a person with 150
   unread notices gets `unread = 100`, the bell shows `99+`, and **"Mark all as read"
   can only clear the 100 the page is holding** — the badge then stays at 99+ after the
   person has done everything the screen offered. That is precisely the failure this
   slice exists to prevent. It is two lines in an existing return to fix (a true count
   plus a `capped` flag). See **N1** and ⚠ **DECISION UX-5**.

2. **At real volume, "All" buries the third group.** I built the HR case with 100 notice
   rows and measured the page: **6,744 px tall on a 1700 px window.** "Waiting on
   someone else" sat below all of it, unreachable in any useful sense, and on a 390 px
   phone it is far worse. Fixed in the design by capping every group at **5 rows under
   "All"**, with the footer wording the product already uses on Home
   (`Showing 5 of 86` · `See all 86 notices`). See **N2**.

3. **A heading whose number does not match the rows beneath it is the same old fault.**
   Under "All" the notices group contains read notices too, so a heading reading
   "3 unread notices" names something other than the list under it. I have changed the
   heading under "All" to **"Notices · 3 unread"**, keeping the brief's exact words
   ("3 unread notices") under the "Unread notices" chip where they are true. **This is a
   deliberate, named divergence from the brief's §6 micro-copy** and I am flagging it
   rather than doing it quietly — ⚠ **DECISION UX-1**.

4. **I still could not sign in as a real employee.** Every demo login on the local bench
   is now caught by the ALV-232 first-use lock (`auth.py:340–380`): nobody on
   `ppj.localhost` has a `last_password_reset_date`, so every staff account with an
   Employee record is redirected to `/update-password`. Changing one would be a write to
   a **shared** bench, which this run is not allowed to do. I captured the real screens
   as `hr@ppj.dev.alvoraa.co` (HR Manager, **no** Employee record, so the lock skips
   them). Everything structural — the navbar, the sidebar, the phone bar, the bell, the
   badge, the two Home cards, every measurement — is real. What I could **not** see is a
   populated Home card, because **PPJ has no pending approvals and no notice rows at
   all** (counted today, §2.3).

---

## 1 · Frame

**Who, when, where.** A line manager on a laptop, on any screen that is not Home,
between meetings; and a frontline employee on a shared factory handset at shift change.
Both asking one question: *is anything waiting for me, and what is it?*

**Personas in scope:** Employee (primary), **frontline employee on a shared handset**
(wins every trade-off), Line manager (the biggest gain), HR Manager (the only one who
hits the caps), CXO (counts by kind).

**Deliberately out of this design:** the sender's side of announcements; who read an
announcement (⚠ COMPLIANCE, brief §10, out of scope, security decides); push, sound and
email; the Desk; the five stale sidebar badges (brief ⚠ PM-8, separate slice).

**The three-persona check.** **CXO:** one row per kind, a badge counting kinds, nothing
changes on Home. **HR Manager:** the same page as everyone, more rows, and the only one
who sees a "Showing the first …" line. **Employee:** a number they can clear by acting,
and one place that answers "where has my leave request got to?".

---

## 2 · Evidence — the real screens, 6 Nov 2026

**The bench was up this time.** `hrlocal-bench`, `hrlocal-proxy`, `hrlocal-mariadb`,
both redis containers, all up 2 hours. Site `ppj.localhost` at `http://127.0.0.1:8010`.
Captured with Playwright (Chrome channel) at **1440 × 900** and **390 × 844**.

**What I changed on the shared bench: nothing.** Every query was a read. No `bench
migrate`, no `clear-cache`, no site config, no record edit. Two in-browser measurements
temporarily un-hid the already-rendered badge inside the page's own JavaScript memory to
read its computed size; nothing was saved and no request was sent.

### 2.1 Measured, not computed — this corrects the scan

| # | What | Measured today | What the scan said |
|---|---|---|---|
| M1 | `--fs-xs` on desktop | **11 px** (`getComputedStyle`) | 11 px — **confirmed, now seen** |
| M2 | `--fs-xs` on a 390 px phone | **12 px** | 12 px — confirmed |
| M3 | `.notif-badge` background | `rgb(179,38,30)` = `--red` `#B3261E` | red — confirmed |
| M4 | `.notif-badge` rendered box | **16 × 16 px**, inside the bell, overlapping the glyph | NB5 — confirmed |
| M5 | Phone bell button | **44 × 44 px** at x = 170, header 56 px tall | passes the phone rule |
| M6 | Frappe navbar on desktop | **1440 × 50 px, and visually empty** except the avatar | the scan inferred this; now seen |
| M7 | Desktop avatar menu | `.nav-link.nav-avatar` **60 × 28 px** at x = 1322 | — |
| M8 | Desktop sidebar nav item | **35 × 38 px**, icon only, **no label** | G2 (icon-only nav) still live |
| M9 | Home cards at 1440 | "Pending for you" and "Notices", **656 × 203 px each**, side by side | — |
| M10 | Phone bottom bar | three items, **129 × 67 px** each | a fourth would make them 97 px |
| M11 | Phone document width | **390 px, no sideways overflow** | — |
| M12 | `--primary` at PPJ | **`hsl(0,0%,0%)` — pure black** (the tenant's brand seed) | new |
| M13 | `--primary` in the dark theme | **`#A99AD4`**, a light purple | new, and it matters — see N3 |

### 2.2 What the screens actually look like

**Desktop (`d-home-vp.png`).** Frappe's navbar is a 50 px white strip holding **one
thing**: the round avatar at the far right. There is no page name visible, no menu, no
bell — about 1,280 px of empty bar. **There is more than enough room for a bell, and
nothing to displace.** Below it, the sidebar is a 35 px icon-only rail with no words at
all, and Home shows "Pending for you" and "Notices" side by side, both in their empty
state with a green tick.

**Phone (`p-home.png`, `p-bell-sheet.png`).** The top bar carries hamburger · "PP
Jewel…" (truncated) · bell · avatar · **Sign out**. It is already full. Tapping the bell
slides up a sheet titled "Notices" with a "Close" link, showing "No notices."

**The existing empty-state voice, which I am reusing word for word:**
"Nothing waiting on you. / Requests that need you, and policies to read, appear here."
and "No notices. / Messages from HR and management, and alerts about your work, appear
here."

### 2.3 Facts I counted in the data, which change two assumptions

Read-only counts on `ppj.localhost`:

| Question | Answer | What it means |
|---|---|---|
| Notification Log rows in total | **2,016** | — |
| Rows of the kinds the bell shows (Grooming Mark, Grooming Review, Announcement) | **0** | **Every notices surface in the product is empty at PPJ today.** The empty state is the only state a reviewer can see on the bench |
| The heaviest single user | **407 rows, 406 unread** — and three more users over 400 | Frappe writes Notification Log rows liberally. These are all `document_type = "Employee"`, so `notices_feed` filters them out |
| Pending leave / expense / advance / shift | **0, 0, 0, 0**; one Attendance Request | No populated Home card exists to photograph |

**What this settles, and what it does not.** The brief's kill criterion 2 — "the heaviest
DTC user carries hundreds of unread notices" — is **not** triggered by what I can see,
because the notice kinds are empty at PPJ. **But four users already carry 400+ rows of
another kind**, and the moment anyone adds a doctype to `NOTICE_DOCTYPES` the page is a
400-row page. That is a cheap, real warning and it is why §6 draws the hundreds case
properly rather than assuming the happy path. **Nobody has counted DTC.** Surbhi has not
authorised that count and I did not run it.

---

## 3 · Benchmark

I am not re-running the scan's benchmark (`01a` §4, six products, every row labelled,
read 6 Nov 2026) and I am not re-labelling it. **No product screenshots were viewed in
either run; Keka's and Gusto's help centres return 403 and Darwinbox's own pages were
not found.** The one line that decides this design stands: *five of six keep "news" and
"tasks" apart, and not one lets reading a notification clear a task.*

One addition from this run, about **what we will not copy**: Workday's bell has an
unread-only toggle **and** cannot delete anything. We are taking the first idea (the
"Unread notices" chip) and the second principle (no dismiss on work owed), and leaving
Workday's filter builder alone.

---

## 4 · Findings

Scan IDs are reused where the problem is the same. New IDs are prefixed **N**.

| ID | Finding | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|
| **N1** | **`notices_feed.unread` is a capped number pretending to be a total.** `unread` is counted from rows already limited to `READ_CAP = 100`. A person with 150 unread sees 99+, and "Mark all as read" clears 100 and leaves the badge at 99+. The badge then cannot be cleared by doing the work — the exact failure the brief §8 is written to prevent | **High** | Fix | S | **P1** | `notices.py:68–75`, read today |
| **N2** | **At 100 notices the page is 6,744 px tall and the third group is unreachable.** Measured in the prototype with the HR dataset | High | Fix | S | **P2** | prototype measurement, 6 Nov |
| **N3** | **A `--primary` badge with white digits fails contrast in the dark theme.** Dark `--primary` is `#A99AD4`; white on it is about **2.1 : 1**, under the 4.5 : 1 rule. The badge's foreground must be its own token (`--on-primary`), not "white" | Medium | Fix | S | **P2** | `design_system.html:15`, measured |
| **N4** | **The heading's number does not equal its list under "All"** (heading counts unread, list holds read rows too) | Medium | Fix | S | P3 | design, §6.2 |
| **NB1** | No bell above 768 px — a laptop user has no global signal | High | Fix | S | P2 | **seen**: navbar is empty but for the avatar (M6) |
| **NB2** | The badge has two boot paths (Home's own paint, plus `ntBellBoot` on a 1,500 ms `setTimeout`), so off Home it arrives up to 1.5 s late with no skeleton. **Part 3 adds a third writer** — a decision taken on the new page must repaint it | Medium | Fix | S | P3 | `portal.js:18393`, `6835`, and `hmDecide` already hand-decrements `sb-team-badge` at 6617 |
| **NB3** | Badge text is 11 px on desktop. Fix inside `.notif-badge`, **never** in `--fs-xs` — `design_system.html` is included by 7 pages | Medium | Fix | S | P2 | M1, M2 |
| **NB4** | Badge is `--red` for an ordinary count | Low | Improve | S | P3 | M3 |
| **NB5** | Badge sits inside the 32 px circle, over the glyph | Low | Improve | S | P4 | M4 |
| **NP1** | A panel with no visible sidebar item cannot be deep-linked or restored; reload and Back both drop to Home | High | New | S | **P2** | `mayOpenPanel`, `portal.js:4707` |
| **N5** | The new sidebar item would copy a live anti-pattern: `.nav-item` is a `<div>` with `onclick`, so the whole rail is unreachable by keyboard. Make **the new one** a `<button>`; leave the other sixteen to their own slice | Medium | New | S | P2 | `frame.html:44–52`, **seen** |
| **N6** | On a 390 px phone in Hindi, "साइन आउट" plus a `99+` badge fills the top bar to its edge. Pre-existing, made more visible by this slice | Low | Improve | S | P4 | prototype, dark + Hindi capture |
| **NC1** | `READ_CAP` truncates silently; `notices_feed` returns no `capped`, while `get_inbox` returns `cap`, `capped` and `shown` per part for exactly this | Medium | Fix | S | P3 | `notices.py:42`, `inbox_api.py:1158–1165` |
| **NC2** | No "mark all as read"; 20 unread ≈ 60 taps | Medium | New | S | P3 | `ntOpenOne` |
| **NX1** | Five sidebar badges painted only after the person opens that panel, while `get_nav_counts` has no caller | Medium | — | M | P3, **out of this slice** | `01a` §2.1 |
| **NX3** | **Every demo login on the local bench now lands on "Set Password"**, because no PPJ user has a `last_password_reset_date`. This blocks browser review of the portal as an employee for *every* agent, not just me | Medium | — | S | P3, **not this slice** | `auth.py`, measured today |
| **K1–K8** | `01a` §2.3 — keep every one | — | Keep | — | — | §2.3 |

**Release view.** No P0. **N1 is a P1** and is a release blocker as written: ship the
badge without it and the first HR person with 150 unread notices has a badge they cannot
clear. The fix is small and it is in scope (the brief already buys two keys on this
return, §5 item 5).

---

## 5 · The number, settled

**Badge = work owed + unread notices.**

```
work owed   = Σ parts[k].count  for k in
              { leave_approvals, expense_approvals, goal_updates,
                attendance_fixes, policies }
              (i.e. every part EXCEPT shift_requests and my_requests)
unread      = notices_feed.unread          ← must be the TRUE count, see N1
badge       = work owed + unread           ← summed in the browser, never a third query
CXO         = (number of KINDS with a count) + unread
display     = "99+" above 99               ← ntPaintBadge already does this
```

**Why it is not `approvals_total`:** that includes `shift_requests`
(`APPROVAL_PARTS`, `inbox_api.py:88`). **Why it is not `d.total`:** that is
`approvals + policies + my_requests` (`inbox_api.py:1132`).

**Home's chip changes to the same definition.** Today `hmPaintPending` computes
`d.total − shift_requests`, which **includes** the person's own requests
(`portal.js:6503`). It becomes the same `work owed` sum. One definition, two surfaces.

**And Home's list gets the same heading**, or the chip above it disagrees with the rows
below it: the person's own requests move under a sub-heading
**"Waiting on someone else · not counted — nothing for you to do yet"** inside the
existing card, under the approval rows. Drawn in the prototype (Screen → "Home — the
changed card").

**One number, one writer.** NB2 says the badge already has two boot paths. The new page
adds a third moment it must move (after a decision taken on the page). **Specify one
function** — `ntPaintBadge(workOwed + unread)` — called from Home's paint, from
`ntBellBoot`, and from `hmDropPending`. Never a second place that computes the number.

---

## 6 · The page, screen by screen, with the exact words

One page, three groups, always in this order. **The order is "what needs you" first**
and it never changes with the filter.

### 6.1 Chrome

| Where | What | Words |
|---|---|---|
| **Desktop** | Bell in Frappe's navbar, **right end, immediately left of the avatar**. 36 × 36 target (desktop floor is 24). Badge **outside** the glyph, top-right corner, 18 × 18, **12 px digits**, `--primary` background, `--on-primary` digits, 2 px ring in `--surface` so it reads against the bar | accessible name: **"Notifications, 7 waiting"** (replaces "Notices, 3 unread") |
| **Desktop** | **A sidebar nav item** — required, or the page loses its address on reload and Back goes Home (NP1). Second in the rail, straight after Home. Bell icon + the word + the same badge. **A real `<button>`** (N5) | **"Notifications"** |
| **Phone** | Unchanged bell at 44 × 44. Only the number and the name change | same |
| **Phone** | **No fourth bottom-bar item.** Three items are 129 px wide; a fourth makes them 97 px for a door that is already one thumb away | — |
| **Page head** | Title, then the window in plain words | **"Notifications"** / **"Last 30 days"** |

### 6.2 The three groups

| # | Heading | Counted in the badge? | Rows | Action in the group head |
|---|---|---|---|---|
| 1 | **"4 waiting on you"** | **yes** | approvals, policies — oldest waiting first, as Home already orders them | — |
| 2 | **"Notices · 3 unread"** under *All* and *To do*; **"3 unread notices"** under the *Unread notices* chip | **yes** (the unread ones) | unread first, then read, newest first | **"Mark all as read"** — notices group only, shown only when there is something unread |
| 3 | **"Waiting on someone else"** + tag **"not counted — nothing for you to do yet"** | **no** | the person's own open requests, with the state sentence `get_inbox` already returns | — |

**Row contents are `ROW_KEYS`, unchanged.** Name · kind · dates · days · amount ·
"waiting N days". **No absence reason, anywhere, ever.**

**The five-row rule under "All" (N2).** Under *All*, each group shows at most **5** rows
and ends with the footer the product already uses on Home:

> `Showing 5 of 86`          `See all 86 notices`

The button sets the chip; it opens no new screen. Under *To do* the work group is whole;
under *Unread notices* the notices group is whole.

### 6.3 The chips

One row, three, mutually exclusive, **nothing ever greyed out**, **no count inside a
chip** (the group heading carries the number).

**"All"** (default) · **"To do"** · **"Unread notices"**

Measured at 390 px: 48 + 67 + 130 px, 44 px tall, 15 px text, total 261 px of 366
available — one row, with room. They wrap at 200 % text by design.

### 6.4 Every state, with its words

| State | What is drawn | The words |
|---|---|---|
| **Loading** | Four grey row-shaped bars, within 300 ms (nfr-budget §2). `aria-busy`, named | "Loading your notifications" |
| **Loaded, something waiting** | The groups above | — |
| **Empty — everything** | One green tick box | **"Nothing waiting on you, and no new notices."** / "Requests that need you, notices from HR, and your own open requests all appear here." |
| **Empty — work only** | tick box in group 1 | **"Nothing waiting on you."** / "Requests that need you, and policies to read, appear here." *(the product's own existing words)* |
| **Empty — notices only** | tick box in group 2 | **"You have read everything."** / "New notices from HR and management appear here." |
| **First morning** (new joiner, both empty) | one box, and it says what the page is **for** | **"Nothing here yet."** / "This is where you will see anything waiting on you, and every notice sent to you. We will put a number on the bell when something arrives." |
| **Notices failed, work loaded** | **Draw what you have.** An amber box in the notices group only; group 1 is normal | **"Could not load your notices."** / "Your work is shown below. Nothing has been lost." · **"Try again"** |
| **Both failed** | One amber box, no groups | **"Could not load this page."** / "Check your connection and try again. Nothing has been lost." · **"Try again"** |
| **Timeout** | The same box. **A spinner always ends.** | as above |
| **Stale row — decided elsewhere** | The row is refused, removed, and a line says why. Never a raw server error, never a silent no-op | **"Already decided by someone else."** |
| **Stale row — withdrawn** | same | **"The request was withdrawn."** |
| **Row no longer theirs** | **Nothing is said.** It is simply gone on refresh — "you no longer approve for Rakesh" leaks an org change | — |
| **Capped work list** | footer inside group 1 | **"Showing the first 50 of 63 attendance fixes"** |
| **Capped notices** | footer inside group 2 | **"Showing the first 100 notices. Older read ones are not kept."** |
| **No permission** | Does not arise. Both calls are scoped to the caller server-side; a person with nothing simply sees the empty state | — |
| **Signed out, then Back** | **Nothing renders.** Acceptance criterion, not a design (PM-AC-B) | — |

### 6.5 What a tap does

| Tapped | What happens |
|---|---|
| A leave or expense row | Opens the existing `hmLeaveSheet` / `hmExpenseSheet` **in place**. Approve or decline with a reason. On success the row leaves, the heading falls, and **the badge falls with it** |
| Any other work row | Navigates through the existing `HM_SCREEN` map. **Marks nothing** |
| A notice | Opens the notice. **Marking it read is correct** — a notice has a read state |
| A "waiting on someone else" row | It is **not a button**. There is nothing to do. The state sentence is the answer |
| A CXO's kind row | Opens that kind's screen. The badge does not move: nothing was decided |

**There is no dismiss, no snooze, no swipe, no X, no "mark done" on a work row. Not in
v1, not later.**

### 6.6 Hindi

Machine drafts. **A native reader must check them before release.**

| English | हिन्दी |
|---|---|
| Notifications | सूचनाएँ |
| All · To do · Unread notices | सभी · करने के लिए · बिना पढ़ी सूचनाएँ |
| {0} waiting on you | आप पर {0} बाकी |
| {0} unread notices · Notices · {0} unread | {0} बिना पढ़ी सूचनाएँ · सूचनाएँ · {0} बिना पढ़ी |
| Waiting on someone else | किसी और के पास |
| not counted — nothing for you to do yet | गिनती में नहीं — अभी आपको कुछ नहीं करना |
| Mark all as read | सभी को पढ़ा हुआ चिह्नित करें |
| Last 30 days | पिछले 30 दिन |
| Showing {0} of {1} | {1} में से {0} दिखाई जा रही हैं |
| Nothing waiting on you, and no new notices. | आप पर कुछ बाकी नहीं, और कोई नई सूचना नहीं। |
| Already decided by someone else. | इसका फ़ैसला कोई और कर चुका है। |
| The request was withdrawn. | अनुरोध वापस ले लिया गया। |
| Try again | फिर कोशिश करें |

All of it goes through `drT()`, which already wraps this block. **Measured:** Devanagari
runs about 30 % longer and the three chips still fit on one 390 px row (§6.3).

---

## 7 · Accessibility (WCAG 2.2 AA, nfr-budget §7)

| Item | What the design does |
|---|---|
| **Text floor** | Badge digits **12 px**, set in `.notif-badge`'s own rule. **Never** raise `--fs-xs` — `design_system.html` is included by 7 pages |
| **Contrast** | Badge `--primary` on `--on-primary`. Light default #5B4B8A on white ≈ **7.6 : 1**; PPJ's black on white = **21 : 1**; **dark theme needs a dark foreground** (N3). The engineer must check all three seeds, including a pale one |
| **Colour is never the only signal** | An unread notice carries a **dot and** the group it is in. The badge carries a **number and** a spoken name ("Notifications, 7 waiting") |
| **Targets** | Phone: chips 44 px, rows 64 px, bell 44 px. Desktop: bell 36 px, nav item 38 px, rows 60 px, **and the "Mark all as read" link is given a 44 px minimum height on the phone** (it measured 32 px until I fixed it) |
| **Keyboard** | Chips are real `<button aria-pressed>` in a named group. Rows are `<button>`. The new nav item is a `<button>` (N5). Focus is a 3 px `--primary` outline everywhere |
| **No focus trap** | The page replaces an overlay, so there is no trap, no Escape handling and no "return focus to the opener" to get wrong |
| **Loading** | `aria-busy` with a name, not a bare spinner |
| **200 % text** | Chips wrap; nothing is `nowrap`; no fixed minimum widths. **Still to test on a real build** |
| **No greyed control** | Every chip is a whole intent, so no combination is invalid |

---

## 8 · Privacy — flagged per `data-doors.md`

**This screen shows another person's data.** Group 1 carries a colleague's name, leave
type, dates, claim amount and note — exactly `ROW_KEYS`, unchanged, for rows the person
is already the named approver of. **No absence reason, no health, no passport, no bank,
no pay.** The slice adds no field.

**The hidden-field warning, stated plainly:** nothing in this design is a protection.
The limit must live in Frappe's permission layer — `get_inbox`'s per-part scope, and
Frappe's own condition on Notification Log pinning `for_user`. **Nobody on this slice
has read Frappe's source for that condition. It is an inference from a docstring and it
must be proved through the API as a plain staff login, on a fresh site** (brief OPS-10).

**The one new exposure this slice creates:** a durable, addressable page holding 30 days
of one person's HR messages, on handsets shared by 441 DTC logins. The design answers it
with behaviour, not decoration:

- Nothing is written to `localStorage` or `sessionStorage` (PM-AC-A). The portal keeps
  exactly one thing today (`sb-pinned`); this must not become the second.
- After `/logout`, Back renders **nothing** (PM-AC-B).
- **A tap on a work row writes nothing**, so a tap from a shared handset leaves no trace
  of who looked.
- **Small groups:** not applicable. Every number on this page is the reader's own.

---

## 9 · Honest about the numbers (nfr-budget → what the person sees)

| The number | What the screen does about it |
|---|---|
| ≤ 500 ms p95 per call, two calls fired together | Skeleton within 300 ms, then the groups. Never a bare spinner |
| ≤ 1.5 s self-service page | The page reuses the warm frame; only the two calls are new |
| **Either call can fail** | **Draw what you have.** One failed feed shows an amber box in **its own group** and the other group renders normally. The bell itself stays as it was — no toast, no blanked page (OPS-6) |
| **The network drops on a shared handset** | Nothing was typed, so nothing can be lost. The words say so: "Nothing has been lost." |
| **A list can hold thousands** | The server caps at 50 per part and 100 notices; the page shows 5 per group under "All" and **says what it is showing**. No design here assumes ten rows |
| **The heaviest user carries hundreds** | Measured: the uncapped page is 6,744 px. The five-row rule (N2) is the answer, and N1 is what keeps the badge honest at that volume |

---

## 10 · The prototype

`C:/Surbhi-Git/hrlocal-data/prototypes/083-ess-notifications/prototype-v1.html`

- **Both widths side by side**, always: 1180 px desktop and 390 px phone. No `vw`
  anywhere; the phone rules are authored once under `.app.ph`.
- Built on the design-system tokens, copied from `design_system.html`, **light and
  dark**, with a tenant-brand switch (Alvora purple / PPJ black) so the badge colour can
  be judged on a real seed.
- Scaffolding uses its own `px-` prefix (`data-px-*`) so it cannot clash with the
  product's `data-v`. The review bar wraps and is **not** sticky.
- **Five people:** line manager (Sakshi Verma, a real PPJ Floor Manager) · employee ·
  HR with a capped inbox (63 work rows, 100 notices, 86 unread) · CXO (counts by kind) ·
  new joiner on their first morning.
- **Six states:** loaded · loading · notices failed / work loaded · both failed · stale
  row refused · after approving two.
- **Two screens:** the notifications page and **Home with its changed card**.
- The chips work. Marking read works. Approving a row drops it and moves the badge.
  The yellow line under the review bar always shows the badge arithmetic.
- Every invented row carries a **Sample** tag, because PPJ has none of this data.

**Looked at once, and fixed what the look showed:** the phone top bar and bottom bar were
stacking vertically (a `display:block` beating a `display:flex`); the Sample tag was
10 px, under our 12 px floor; "Mark all as read" was a 32 px target on the phone. All
three fixed before saving. **Measured after:** no sideways overflow at 390 px, no text
under 12 px, no phone target under 44 px, no JavaScript errors.

---

## 11 · Checks before handoff

**Nielsen, the ones that bite here.** *Visibility of system status* — the badge is the
status, and it only moves when the work moves. *Match with the real world* — "waiting on
you" and "waiting on someone else" are how people say it. *User control* — a tap on work
owed is reversible because it does nothing; a decision has its own sheet with a reason
box. *Recognition over recall* — the group heading carries the number so nobody has to
remember what the badge counted. *Error recovery* — every failure says what to do and
offers "Try again". *Minimalist* — three chips, two counted groups, one uncounted.

**Persona walkthrough — steps to the top task.**

| Persona | Task | Today | After |
|---|---|---|---|
| Line manager, laptop, on Attendance | Approve Rakesh's leave | **no signal at all**; go Home → read the card → open the row → decide = 4 | see the bell → click → decide in place = **3, from any screen** |
| Frontline, shared handset | "Anything waiting?" | bell → sheet → **notices only**, silent about work | bell → page → work first = **2 taps, under two minutes** |
| Employee | "Where has my leave got to?" | Leave panel → find the row | bell → "Waiting on someone else" = **2 taps**, and it never inflates the badge |
| HR, 86 unread | Clear the backlog | ~258 taps | "Mark all as read" = **2 taps** (subject to N1) |
| CXO, phone, five minutes | One number | — | badge = kinds + unread; three rows with counts |

**The frontline bar: can it be done in two minutes on a phone?** Yes — bell, page,
first row is the oldest thing waiting. Nothing to read before acting.

**Refusals check.** No read-tracking. No ranking. No AI. No dark pattern — the empty
state is never hidden, there is no nagging loop, no pre-ticked anything, and no hidden
way out. **No absence reason anywhere.** The one-way rule holds: the manager gains a
signal and the employee gains a number they can clear.

**Red team.**

- *Brand new person?* The first-morning state says what the page is **for**.
- *Expert in a hurry?* "To do" is one tap from the bell.
- *No data?* Empty states, and the empty state is never hidden.
- *100× the data?* Measured. Five rows per group under "All", with the real total named.
- *Network drops mid-action?* Nothing is typed on this page. A decision sheet has its
  own "it may have gone through" handling already (`mayHaveGone`).
- *Not allowed to see something?* Both feeds are scoped server-side; there is nothing to
  hide on the page.
- *A number they cannot explain?* The two headings reconcile the badge in words, on
  screen, every time.
- *Can they recover without calling support?* Every failure has "Try again"; every stale
  row says why in plain words.

---

## 12 · What the business analyst must turn into acceptance criteria

1. **Badge = Σ parts[k].count for every part except `shift_requests` and `my_requests`,
   plus `notices_feed.unread`.** Summed in the browser from the two answers already
   drawn. Never a third query. Never `d.total`. Never `approvals_total`.
2. **Home's "Pending for you" chip uses the same sum**, and the person's own requests
   move under the sub-heading "Waiting on someone else" inside the same card.
3. **One function paints the badge**, called from Home's paint, from `ntBellBoot` and
   after a decision. A test should assert the badge equals the sum of the drawn groups.
4. **Tapping a work row marks nothing.** No write of any kind. Test it by asserting no
   request is sent.
5. **No dismiss, snooze, swipe or mark-done on a work row**, and a stale tap shows
   "Already decided by someone else." / "The request was withdrawn." A row that stopped
   being theirs says **nothing**.
6. **"Mark all as read" exists in the notices group only** and can never reach a work
   row.
7. **The true unread count** (N1): `notices_feed` returns an uncapped `unread` and a
   `capped` flag, and the page says "Showing the first 100 notices…" when it bit.
8. **Each group shows at most 5 rows under "All"**, with "Showing {0} of {1}" and a
   button that sets the chip.
9. **A sidebar nav item exists and is visible**, or reload and Back are broken
   (`mayOpenPanel`).
10. **The badge is 12 px, set in `.notif-badge`.** `--fs-xs` is unchanged. A test should
    fail if `design_system.html` is touched by this slice.
11. **Badge colour `--primary` with its own foreground token**, checked for 4.5 : 1 in
    light, dark and against a pale brand seed.
12. **Nothing in `localStorage` or `sessionStorage`** (PM-AC-A), and **Back after
    `/logout` renders nothing** (PM-AC-B).
13. **Either call may fail alone**: the other group still renders, the bell is unchanged,
    there is no toast, and the failed group offers "Try again".
14. **Hindi at parity** for every string in §6.6.
15. **Door list on Notification Log as a plain staff login, on a fresh site** (OPS-10),
    before anyone calls this slice safe.

---

## 13 · Usability test plan — for the High-impact items

Five people, 10 minutes each, own device, no training.

| Who | Task | Success | What would change the design |
|---|---|---|---|
| 2 × frontline, shared Android, Hindi | "Something is waiting for you. Deal with it." | Reaches the right item from the bell in **under 2 minutes**, first try | If they open "All" and scroll past work to notices, the page opens on **To do** |
| 1 × line manager, laptop | "Approve anything your team is waiting on." Then "Is anything else waiting?" | Approves from the page; says the badge went 7 → 6 and can say why | If they expect the badge to drop when they **read** the page, the merged badge is wrong and we fall back to two numbers |
| 1 × employee | "Where has your leave request got to?" | Finds it under "Waiting on someone else" | If they look under "To do", the third group needs a different name |
| 1 × HR | "Clear your notices." Then "What is this number counting?" | Uses "Mark all as read"; explains the badge in one sentence unprompted | If they cannot explain it, the group headings are not doing their job |
| all five | Show "Notices · 3 unread" and "3 unread notices" (⚠ UX-1) | They read both as the same idea | If either confuses them, settle on one wording and add the reconciling footer |

**The one question I most want answered:** does a merged badge make people trust it more,
or less? That is the whole bet.

---

## 14 · Subtract pass

Read once more asking only *what can I delete?* **Removed from this design:**

- **A "Notifications" entry in the phone bottom bar.** Measured: it would take the three
  existing items from 129 px to 97 px for a door already one thumb away.
- **A per-group "collapse" control.** The five-row rule plus the chips does the same job
  with no new control.
- **A sort control, a date picker, a search box, a sender filter, per-kind filters, a
  fourth chip, per-chip counts, saved views, per-row read toggles** — all named and
  refused in `01a` §6, all still refused.
- **A second "See all" destination.** The footer button sets an existing chip; it opens
  nothing new.
- **A new empty-state illustration.** The product's existing green tick is reused.
- **New empty-state wording for two of the five states.** I used the product's own
  sentences, read off the live screen, rather than writing better ones.
- **A confirm on "Mark all as read".** It is reversible by reading nothing — it destroys
  no work. A confirm here would be a nag.
- **A "last updated" timestamp on the page.** `HM_STALE_MS` already refreshes; a clock
  is a thing to explain.

**Kept despite the pass, each with a named reason:** the sidebar nav item (without it the
page cannot be reloaded); the third uncounted group (nothing else answers "where is my
request?"); the five-row footer (without it the page is 6,744 px); the capped line (the
sibling endpoint already sets the honesty standard); "Mark all as read" (258 taps).

---

## Open questions

| # | Decision needed | Context and conflict | Who is affected | Options | My recommendation | Risk if it waits | Owner |
|---|---|---|---|---|---|---|---|
| ⚠ **UX-1** | Under "All", does the notices heading read **"Notices · 3 unread"** or the brief's **"3 unread notices"**? | The brief's §6 WOW uses the second. Under "All" the list also holds **read** notices, so the second heading names something other than its own list — the "a count must equal the list it links to" rule that slices 034/042/076 exist to protect | everyone | **A** heading names the list, the unread count is a tag beside it (**drawn**). **B** the brief's words everywhere, plus a footer reconciling it | **A.** It is one word's difference and it keeps the rule intact. **I have diverged from the brief here and I am saying so rather than doing it quietly** | Low — it is one string | **Surbhi** |
| ⚠ **UX-2** | Three chips, or a fourth **"Notices"** so read ones are reachable without "All"? (carries ⚠ 1 / PM-3) | A fourth chip is the first step to eight | everyone | three / four | **Three.** "All" reaches read notices, and under the five-row rule "All" is now genuinely readable. **Low confidence; it is one line to change and §13 tests it** | None | **Surbhi** |
| ⚠ **UX-3** | For a CXO, does the badge count **rows or kinds**? (carries ⚠ 2 / PM-4) | A badge reading "214" on a five-minute phone check is noise, and `ntPaintBadge` already shows "99+" above 99, so rows would read "99+" permanently and never move | CXO only | rows / **kinds** | **Kinds**, matching Home's own CXO shape (`hmIsCxo`). A kinds badge is 1–5 and moves when a queue empties | Low | **Surbhi** |
| ⚠ **UX-4** | Badge colour: **`--primary`** or red? (carries ⚠ 3 / PM-5) | Red for an ordinary count is on our anti-pattern list **three times** (PF4, LV9, NB4). We have no overdue concept on this page, so red would mean nothing | everyone | red / **`--primary`** | **`--primary`**, and **I am holding this line.** One CSS line. It must come with its own foreground token (N3) or it fails contrast in the dark theme | Low | **Surbhi** |
| ⚠ **UX-5** | **N1 — the capped unread count.** Does `notices_feed` return a true, uncapped `unread`? | **This is a P1 and I think it is a release blocker.** As built, a person with 150 unread cannot clear the badge by doing everything the screen offers. The brief already buys two keys on this return (§5 item 5), so it is the same rung | HR and any long-serving employee | **A** true count + `capped` flag (two lines, one extra `count` query). **B** ship as is and accept a badge that sticks at 99+ | **A.** B breaks §8's own sentence — "a number they can trust, act on, and watch fall to zero" | **High.** Found after the brief gate; if it is not settled the slice ships a badge that can lie | **Surbhi**, with `hrms-fullstack-engineer` on the query cost |
| ⚠ **UX-6** | The five stale sidebar badges (⚠ 5 / PM-8) are out of scope. **In one line, what will a person see?** | — | everyone on desktop | — | **A trustworthy bell beside five numbers that are blank until you open the panel they belong to** — so "Leave" shows nothing while the bell says 7 includes two leave requests, and the person learns the sidebar is not to be trusted. Record it, do not fix it here | Low | noted, **`hrms-product-manager`** owns the follow-up slice |
| ⚠ **UX-7** | **NX3** — every demo login on the shared bench now lands on "Set Password" | No PPJ user has a `last_password_reset_date`, so the ALV-232 lock catches all of them. This blocks browser review of the portal as an employee for **every** agent, in every future slice | every agent | — | Somebody with permission should set `last_password_reset_date` on **one** demo employee on the local bench and record which. I did not, because the bench is shared and this run is read-only | Medium — it will cost the next four slices an hour each | **Surbhi** or `hrms-devops-engineer` |
| Evidence required | How many Notification Log rows of the **notice kinds** does the heaviest **DTC** user carry? | PPJ has **zero**, so it tells us nothing about DTC. The brief makes this a kill criterion | HR, long-serving staff | — | A read-only count, ten minutes. **Not run** — Surbhi has not authorised it and I did not run it | Medium | **Surbhi** to authorise |
| ⚠ **COMPLIANCE** | May an announcement sender see **who read** their notice? | Out of scope per the brief; named here so it is not lost | the least powerful person in the picture | — | Out of scope. Its own slice, with counsel | None here | `hrms-security-privacy-engineer`, then **Surbhi** |

---

## Assumptions

- `[ASSUMPTION]` **The heaviest DTC user carries single-digit unread notices.** Unverified
  — PPJ carries zero of the relevant kinds, which proves nothing about DTC. **The design
  works either way:** the five-row rule and the capped lines are drawn for the hundreds
  case. What breaks if it is hundreds is **N1** — the badge sticks at 99+ and "Mark all
  as read" cannot clear it — which is why UX-5 matters more than it looks.
- `[ASSUMPTION]` Reusing `hmLeaveSheet` / `hmExpenseSheet` on the new page is clean. If
  it is not, drop approve-from-the-page to "later" rather than writing a second sheet.
- `[ASSUMPTION]` A bell fits in Frappe's navbar without fighting the template. **Strongly
  supported by measurement:** the bar is 1440 × 50 and holds one 60 px avatar.
  `hrms-fullstack-engineer` still confirms (PM-6).
- `[ASSUMPTION]` Both calls answer inside the ≤ 500 ms p95 budget at DTC's ~600 staff.
  The only measurements are slice 044's, September 2026, on fixture sites. OPS-3 closes it.
- `[ASSUMPTION]` Frappe's own permission condition on Notification Log pins `for_user`.
  **Nobody has read Frappe's source. It is an inference and must be proved through the
  API** (OPS-10).
- `[recall — verify]` Competitor rows are from `01a` §4; no product screenshots were
  viewed in either run.
- Hindi is a machine draft and needs a native reader.
- Every invented row in the prototype carries a **Sample** tag. PPJ has no notice rows
  and no pending approvals, so nothing on this page could be drawn from real data.

---

## Handoff note

**To `hrms-business-analyst`.** §12 is your list. The three that must not be softened are
the badge formula, "tapping work owed writes nothing", and "no dismiss on a work row".
Add to them the one I found today: **N1 / ⚠ UX-5 — `notices_feed.unread` is capped at 100
and is not a true count.** Ship without that fix and an HR user's badge sticks at 99+
after they have done everything the page offers; the badge then fails the brief's own
success measure 4 on day one, and I would not call the slice release-ready. The Access
expectations table in the brief §9 is still yours to turn into per-field rules with the
Frappe door named for each — and the most important row is still the one saying the limit
must **not** live in our page code.

**To `hrms-product-manager`.** I have diverged from your §6 micro-copy in exactly one
place and I am naming it: under "All", the notices heading reads **"Notices · 3 unread"**
rather than "3 unread notices", because under "All" the list holds read notices too and a
heading must name its own list. Your words survive unchanged under the "Unread notices"
chip. ⚠ UX-1 is yours and Surbhi's to settle; it is one string either way. Everything
else in the brief I have taken as given, including the two decisions Surbhi settled
today.

**To `hrms-devops-engineer` (§2 Design).** Two things from this run: the badge now has a
**third** moment it must repaint (after a decision on the new page), so OPS-11's "no
cache" is more important, not less; and ⚠ UX-5 adds **one count query** to
`notices_feed` — please say whether that threatens the ≤ 12 statement assertion in
`test_notices_076.py`.

**To whoever publishes this.** The prototype is at
`C:/Surbhi-Git/hrlocal-data/prototypes/083-ess-notifications/prototype-v1.html`. I could
not publish it. Please put the link in front of Surbhi with the design, and bring her
feedback back — I log every point in `ux-learnings.md` and build `prototype-v2` rather
than overwriting v1.
