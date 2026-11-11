---
slice: 083-ess-notifications
artifact: 01a-ux-opportunities.md
author: hrms-ux-designer (opportunities scan)
date: 2026-11-06
status: evidence for the PM's brief. I recommend; Surbhi decides. No prototype at this stage.
inputs: [ux-learnings.md, no-over-engineering.md, product-context.md §2 §6, nfr-budget.md §1 §2 §5 §7, handoff-contract.md, docs/slices/076-home-notices/01-product-brief.md, notices.py, inbox_api.py, portal.js, frame.html, parts/home.html, parts/drawers.html, frame.css, panels.css, design_system.html, ALV-288-ess-routing/00-impact-analysis.md]
---

# 083 · A notifications bell and page on the employee portal — UX opportunities

**Bad news first, three things.**

1. **The hard problem is not the bell. It is the word "read".** A notice is *read or
   unread*. An approval is *done or not done*. If one badge counts both and reading
   clears both, the badge lies about work. Zoho People's own users report exactly this
   failure (§4). My recommendation is in §5, and it costs nothing extra to build — but
   it is a product decision, not a layout one.

2. **I could not look at a screen.** Docker Desktop is not running on this machine
   (`docker ps` fails: *cannot find the pipe*), so there is no `hrlocal-bench` and no
   bench console. Everything below is **read from the code in this worktree on
   6 Nov 2026**, and every measurement is computed from the CSS tokens, not observed.
   Anything that needs eyes is named in §9.

3. **One measured number blocks a clean desktop bell.** `--fs-xs` is **11 px** on a
   laptop and only becomes 12 px under `@media(max-width:768px)`
   (`frame.css:332`). The badge uses `--fs-xs` (`panels.css:1482`). So a desktop bell
   built from today's CSS ships 11 px digits, under our own 12 px floor. It is a
   one-line fix *in the badge rule*, not in the shared token — see §9, NB3.

---

## 1 · Frame

**Who, when, where.** An employee or a line manager, at any moment on any screen of the
employee portal, on a laptop or a phone, asking one question: *is anything waiting for
me, and what is it?* Today they can only answer it properly by going to Home, and on a
laptop they get no signal at all until they do.

**Personas in scope:** Employee (primary), **frontline employee on a shared handset**
(wins every trade-off — product-context §2), Line manager (the biggest gain), HR Manager
(as a reader, not as a sender), CXO.

**Deliberately out of scope of this scan:** the *sender's* side of announcements (slice
076 Part B already shipped it, and nothing in ALV-322 asks to change it); push
notifications; email; the Desk.

---

## 2 · Current state — read from code, 6 Nov 2026

### 2.1 How many surfaces already answer "what needs my attention?"

Surbhi counted three. **The count is three for the two feeds, and eight for "a number
that tells me something is waiting".** Five of those eight do not come from either feed.

| # | Surface | Fed by | Desktop | Phone | Fact / evidence |
|---|---|---|---|---|---|
| S1 | Home card **"Pending for you"** | `inbox_api.get_inbox` | yes | yes | `parts/home.html:43`; `hmPaintPending`, `portal.js:6655` |
| S2 | Home card **"Notices"** (5 unread) | `notices.notices_feed(see_all=0)` | yes | yes | `parts/home.html:54`; `homeNotices`, `portal.js:6811` |
| S3 | **The bell** + badge | the same `notices_feed(see_all=0)` count; opens `see_all=1` | **no** | yes | `frame.html:135`; `.mob-header` is `display:none` (`frame.css:231`) and only shown at `@media(max-width:768px)` (`panels.css:367`) |
| S4 | Sidebar badge, **Leave** | `loadLeaves` counts Open applications in the browser | yes | — | `portal.js:9441` |
| S5 | Sidebar badge, **Performance** | `goals_api.get_portal_context` → `dashboard.at_risk` | yes | — | `portal.js:15631` |
| S6 | Sidebar badge, **Policies** | `get_my_policies.pending` | yes | — | `portal.js:4883` |
| S7 | Sidebar badge, **Team View** | the Team panel's own call, then decremented by hand on approve | yes | — | `portal.js:12948`, `12893` |
| S8 | Sidebar badge, **Data to review** | `drSetBadge` from the Data-review call | yes | — | `portal.js:13204` |

**The finding that matters for the brief.** `inbox_api.get_nav_counts` exists, is
whitelisted, is tested, and computes every one of those numbers from one filter
per part. **Nothing on the live portal calls it.** Its only callers are
`next-frame.js` (the discarded redesign) and the two measurement scripts
(`grep get_nav_counts` across the app, 6 Nov 2026). So S4–S8 are five numbers from five
different queries, each painted **only after the person opens that panel** — a badge
that appears when you have already arrived is not a notification.

**I am not proposing we fix S4–S8 in this slice.** It is scope creep. I am recording it
because a bell that shows a trustworthy total makes five stale per-panel badges
*more* visibly wrong, and the PM should decide whether they are removed with the bell or
left alone (⚠ DECISION 5).

### 2.2 What an employee can and cannot find today — the honest list

**Can:**

- See five unread notices and the oldest pending items, **on Home only**.
- On a phone, see one number anywhere in the product and tap it (S3).
- Open the last 30 days of notices, unread first, from the Home card's "See all" footer —
  **this works on a laptop too**, so the destination exists; only the global
  affordance is missing. (Correcting a reasonable reading of the ticket: it is not
  "there is no way to see all notices on a laptop", it is "there is no way to know
  there is anything to see unless you are on Home".)
- Read one notice in a sheet. Opening it marks it read (`ntOpenOne`, `portal.js:6887`,
  via Frappe's own `mark_as_read`).

**Cannot:**

- See on a laptop that anything is waiting, without going to Home.
- See a pending approval in the bell at all. The bell is notices-only.
- Reach a **read** notice older than 30 days. Ever. `SEE_ALL_DAYS = 30`
  (`notices.py:41`) drops read rows; unread rows survive for ever. There is no
  search, no date filter and no second page.
- Know when the list was cut. `READ_CAP = 100` truncates silently. `notices_feed`
  returns no "capped" key, unlike `get_nav_counts`, which carries `cap` and `capped`
  precisely so a screen can say *"Showing the first 50 of 60"*. Two sibling endpoints,
  two standards of honesty.
- Clear a backlog. There is **no "mark all as read"**. Twenty unread notices is
  twenty × (tap row → read → close sheet) ≈ **60 taps**.
- Filter anything. The sheet is one list, in one order.
- Deep-link or bookmark any of it. Both the Home sheet and the bell sheet are
  overlays with no address.

### 2.3 Keep — things that are right and must survive the merge

| ID | Keep | Why it matters |
|---|---|---|
| K1 | **One function feeds the card and the bell** (`notices_feed`). The card's "N unread" *is* the badge. | This is the guarantee the 076 comment at `portal.js:6400` exists to protect. Any merge must keep "the number equals its list". |
| K2 | **`for_user` = the caller, plus Frappe's own permission condition on Notification Log**, plus `grooming._readable` per row. | A colleague's notice cannot come back whatever the client sends. This is the data-doors rule honoured in the permission layer, not the page. |
| K3 | **Fixed field list out** — name, sentence, link, time, read. No reasons, no ids. Same discipline as `inbox_api.ROW_KEYS`. | New fields are a deliberate, reviewed act. |
| K4 | **Every string goes through `esc()`** before `innerHTML`. | A notice written as `<img src=x onerror=…>` renders as characters. |
| K5 | **Shift requests are listed and counted nowhere** on Home, with a named reason: no screen exists where a manager decides one (`hmPendingRows`, `portal.js:6592`), and the total subtracts them to match. | The honest version of "hide what a person cannot use". It must stay out of the bell for the same reason. |
| K6 | The 30-day read-notice window. | Workday's own business-process notifications also disappear after 30 days (§4). We are not out of step. |
| K7 | A CXO sees **one row per kind with a count**, not 400 names (`HM_KIND`). | Keeps the CXO's five minutes usable. |
| K8 | The system sender is shown as **"Alvora"** — one trailing a, correct brand. | Do not "fix" it. |

### 2.4 Two structural facts the design must obey

**F1 — a panel with no visible sidebar item cannot be deep-linked or restored.**
`mayOpenPanel` (`portal.js:4707`) answers "may this person open this screen by typing or
reloading its address?" by looking for `.nav-item[data-panel="…"]` whose
`style.display !== "none"`. Home and My profile are the only hard-coded exceptions. So a
notifications **page** reached only from the bell would: lose its address on reload,
and send Back to Home. If we want a real page, it needs a sidebar nav item — which is
also the "words, not just icons" answer for a laptop.

**F2 — there is no desktop top bar of ours.** The desktop chrome is Frappe's own website
navbar (`nav.navbar`, fixed, full width, `frame.css:30`), which the portal already
treats as its top bar: slice 070 writes the page name into `a.navbar-brand span`
(`portal.js:4786`) and `frame.css` hides the navbar's brand and its two desk doors
(`#website-post-login .switch-to-desk`, `.apps`). The phone bar `.mob-header` is a
separate element that is `display:none` above 768 px.

---

## 3 · The cost ladder — where this slice sits

| Rung | Verdict |
|---|---|
| 1 · Already there | **Rejected, with a fact.** Frappe's notification dropdown is a **Desk** UI. The ESS portal is a website page; its navbar is Frappe's *website* navbar, which carries a post-login avatar menu and no bell. `[recall — verify]` on the Desk dropdown's exact tabs; the relevant fact — that no website-side notification component ships — is confirmed by the portal having had to build `notices_feed` and its own bell in slice 076. |
| 2 · Configuration | Nothing to configure. There is no setting that shows a bell on a laptop. |
| 3 · Customisation | A Notification or Workflow sends messages; it does not draw a screen. |
| **4 · New code — front end only, on two endpoints that already exist** | **This is the whole slice.** One button in the desktop chrome. One new `parts/*.html` panel + one sidebar nav item (F1) + JS, calling `notices_feed(see_all=1)` and `get_inbox()` — **the same two calls Home already makes**. CSS for the badge floor. |
| 5 · New DocType | **Rejected, and this is load-bearing.** The only thing that would need storage is a per-task "seen" flag, so the bell could mark a task seen without marking it done. §5 recommends we never have one. No flag, no field, no DocType. |
| 6 · New app | No. |

**Server-side change needed: I believe none.** Both endpoints already return everything
the page needs. Two honest caveats for the engineer, not reasons to build more:

- The page makes **two** calls, not one. At the NFR budget of ≤ 500 ms p95 per
  whitelisted call (nfr-budget §2) and with the frame already warm, two parallel calls
  are inside the ≤ 1.5 s self-service budget. **Do not build a merged endpoint** to save
  one round trip — that is a third filter expression over the same data, which is the
  exact thing `inbox_api`'s docstring forbids.
- `notices_feed` should gain **two keys it already knows**: whether the 100-row read cap
  bit, so the page can say so (NC1). That is two lines inside the existing return, not a
  new surface.

---

## 4 · Benchmark — whole products, and what their bell actually holds

Every claim below is labelled. **No trial accounts; no product screenshots viewed in
this run.** Keka's help centre returned HTTP 403 to a direct fetch (as `ux-learnings`
predicted) and Gusto's returned 403, so those rows are from search-result summaries.

| Product | Is there a bell? | What is in the bell | Is "work owed" somewhere else? | Filters offered | Label |
|---|---|---|---|---|---|
| **Workday** | Yes, with a count | **Informational only.** University admin guides are explicit: *"My Tasks are items that you need to take action on while notifications are solely informational."* Notifications **cannot be deleted**; there is an **unread-only toggle**; business-process notifications **disappear after 30 days** | **Yes — "My Tasks"**, a separate inbox, formerly called Inbox | **On My Tasks, not the bell**: business-process type, custom conditions, max row count; built-in views Favorites, Overdue, Delegated to Me | read via search summaries of several university Workday guides, 6 Nov 2026 (GVSU, Stevens, Mt Holyoke, Lynn). Tenant- and version-dependent |
| **Keka** | Yes, and it is **new** | Real-time alerts, a sound, mark-as-read in the dropdown. Keka's own framing: so users see time-sensitive items **without waiting for them to surface in the Inbox** | **Yes — the Inbox**, left nav, its own count badge, a **"Take Action"** tab for pending tasks and a separate **Notifications** section inside it | Tabs inside the Inbox; none named on the bell | read via search summary of `help.keka.com` article 39946785952657 and `support.keka.com` 84000386502, 6 Nov 2026. Direct fetch 403 |
| **Zoho People** | Yes `[recall — verify]` | **The evidence that decides our design:** a Zoho People community post reports *"There's no way to tell if you performed the task that the notification relates to because if you look at it, it marks it as read."* | Approvals inbox across modules `[recall — verify]` | Not found | the complaint: read via search summary of a `help.zoho.com` People community topic, 6 Nov 2026. I could not find an official Zoho People bell article |
| **BambooHR** | **No bell for tasks.** An **inbox icon** top-right with a number | — | **Yes, two things**: the inbox icon, and a **"Needs Your Attention" widget** at the top of Home that *"remains hidden until there's something new"*, groups requests **by type**, expands to show dates/balances, and ends with a caught-up confirmation. Admins and managers choose which **categories** appear | **Category on/off per person**, in the widget's Edit menu — a personalisation, not a filter bar | read on `bamboohr.com/product-updates/needs-your-attention-widget-beta`, 6 Nov 2026 (page carries no date; marked Beta). Inbox detail read via search summary of the older ScreenSteps help |
| **greytHR** | Yes — **"Message Center"**, with an unread dot/count | Bulletin-board posts, payslip releases, published letters | **Yes — "To Do > Tasks"**, with an **Open** tab | Not found beyond the Open/closed tabs | read via search summaries of `greythr.freshdesk.com` 1060000051286, 1060000048785, 1060000051297 and `greythr.com/help-ess-web`, 6 Nov 2026; articles undated or 2024–25 |
| **Darwinbox** | `[recall — verify]` | Third-party pages describe real-time alerts for pending approvals, deadline reminders and HR updates; its engagement product has e-noticeboards reaching people **without a corporate email** | `[recall — verify]` | Not found | **I could not find Darwinbox's own help pages** for the bell or a task list. Everything here is third-party or marketplace copy, 6 Nov 2026 |
| **Gusto** (not a competitor; included because the pattern is clean) | Yes | *"two tabs: Tasks and Activity"* | Same bell, different tab | Two tabs | read via search summary of `support.gusto.com` article 178361225624246, 6 Nov 2026. Direct fetch 403 |

**What the market actually says, in one line: five of six keep "news" and "tasks"
apart, and the two that put them together put them in different tabs.** Not one of them
lets reading a notification clear a task. Workday says it in a sentence; Keka splits bell
from Inbox; BambooHR does not use a bell for tasks at all; Zoho People merged the read
state and its users complain about precisely the confusion we are about to design.

**Every one of them also keeps a Home widget as well as the bell** (BambooHR's "Needs
Your Attention", Keka's Inbox tile, greytHR's homepage bell, Workday's My Tasks
landing). That is market evidence against deleting our Home "Pending for you" card.

### What we will deliberately not copy

| Not copying | Why |
|---|---|
| **Workday's filter builder** (business-process type, custom conditions, row-count caps, saved views) | Our HR person is one person with tens of rows, not a shared-services team with thousands. Our frontline user has a 360 px screen. A filter builder is a surface to maintain for nobody. |
| **Keka's sound and browser-permission prompt on first login** | A sound on a shared factory handset belongs to whoever is holding it, and an Android permission prompt out of nowhere gets "Don't allow" (`ux-learnings`, slice 013). If push is ever wanted it is its own slice, with its own "explain before the system asks" screen. |
| **BambooHR's per-category on/off personalisation** | It lets a manager switch off the category their colleagues are waiting in. Our version of "I don't want to see this" is *do the work*, not *hide it*. |
| **BambooHR's widget hiding itself when empty** | Our Home card is "never hidden" on purpose, and an empty state that says "Nothing waiting on you" teaches people the card exists and is trustworthy. A card that only appears when there is bad news trains people to dread it. |
| **Zoho People's "opening marks it read"** applied to tasks | §5. This is the whole slice's risk in one behaviour. |
| **Any feed, like, comment, poll or rich media** | Settled in slice 076 and unchanged. |
| **A second number for "all notifications ever"** | We have no archive and no search. Promising history we cannot serve is worse than the 30-day window. |

---

## 5 · The hard design problem — my recommendation

The three questions, answered in order, with the reasoning.

### 5.1 Does the bell's number stay the same as Home's Pending number, split in two, or swallow it?

**Recommendation: one bell, one badge, one number — and the Home "Pending for you" card
stays, with its own count, as a visible subset.** The numbers reconcile on screen, in
words, so they can never *appear* to disagree.

| Option | What the person sees | Verdict |
|---|---|---|
| **A · Two numbers in two places** (bell = unread notices; Pending card = work) | Today's product plus a desktop bell. Honest, but the bell still cannot tell a manager that four approvals are waiting — which is the point of ALV-322 | Rejected: it does not deliver the ticket |
| **B · One merged number, Pending card deleted** | One badge, one page, nothing on Home | Rejected. Home is the landing screen; losing the at-a-glance means every morning starts with a tap. And all six benchmarked products keep a Home surface *as well as* a bell (§4) |
| **C · Two numbers in one place** (badge shows "4 · 3" or two dots) | A badge a person must decode | Rejected. A badge has room for one idea. `ux-learnings` already carries "state in words beside the colour", and two numbers in 16 px is the opposite |
| **D · One merged number, Pending card stays and is named as part of it** ✅ | Bell badge **7**. The page's two group headings read **"4 waiting on you"** and **"3 unread notices"**. Home's Pending chip reads **"4 waiting"** — the same 4, from the same call | **Recommended** |

**Why D is safe for the K1 guarantee.** The 076 comment protects *"the number and the
list cannot disagree"*. Under D, each group's number still comes from exactly one
function over exactly one filter: the task number from `get_inbox`, the notice number
from `notices_feed`. The badge is their **sum, computed in the browser from the two
answers it just drew** — never a third query. Nobody writes a filter "just for the
badge", which is the thing the comment forbids.

**Define the badge precisely, because "total" is wrong.** `get_inbox`'s `total` is
`approvals + policies + my_requests`. **My own pending leave request is not work owed to
me** — there is nothing I can do about it, and counting it makes the badge a number I
cannot reduce. So:

> **Badge = unread notices + approvals waiting on me + policies to acknowledge.**
> That is `notices_feed.unread + get_inbox.approvals_total + policies.count`, minus
> shift requests (K5 — no screen decides them), and **excluding `my_requests`.**

`my_requests` rows still belong **on the page**, under a third, uncounted heading —
"Waiting on someone else" — because "where is my leave request?" is a real question and
this is the one place that answers it. It just never inflates a number the person cannot
act on.

**The two-minute phone test.** Open the page from the bell: the first thing under the
heading is the task group, oldest first (`waiting_since` ordering already exists). One
tap to the item. Nothing to read before acting.

### 5.2 What happens when someone taps a pending approval in the bell?

**Recommendation: it navigates. It marks nothing. Ever.**

Three reasons, strongest first:

1. **A task has no read state to mark.** `Notification Log` rows have `read`; leave
   applications, expense claims and policies do not. Marking a task "read" would need a
   new field — rung 5 of the ladder, for a behaviour nobody asked for.
2. **Zoho People's users have already run this experiment for us** (§4): once opening
   marks read, you cannot tell whether the work was done. That is the badge becoming
   decorative.
3. **It is the privacy-safe default.** Marking nothing means no write, so a tap from a
   shared handset leaves no trace of who looked.

**And where it does navigate matters.** A leave or an expense row should open the same
decision sheet Home already opens (`hmLeaveSheet`, `hmExpenseSheet`), so a manager can
approve from the notifications page without a second journey — "let people act where
they see the problem". That is reuse of an existing component, not new design. Everything
else routes through the existing `HM_SCREEN` map.

**Notices keep today's behaviour unchanged:** opening one marks it read, through Frappe's
own `mark_as_read`. **Plus one addition I do recommend: "Mark all as read", in the
notices group only** (NC2 — it is 60 taps today). It must be in the notices group's own
header so it is visibly scoped to notices and can never reach a task.

### 5.3 Does an item that is work owed ever leave the list without the work being done?

**Recommendation: no — with exactly three exceptions, each of which must say so.**

There is **no dismiss, no snooze, no swipe-away, no "mark done", and no X** on a task
row. Not in v1, not later. A task leaves the list only because `get_inbox`'s filter
stopped matching it, which happens in three legitimate ways:

| It disappears because | What the person should see |
|---|---|
| Someone else decided it (an alternate approver, or HR stepping in) | On a refresh it is simply gone — correct. But if they tap a **stale row** from a page open since this morning, the server will refuse; the screen must say **"Already decided by someone else."** Never a raw server error, and never a silent no-op. |
| The person who raised it withdrew it | Same: **"The request was withdrawn."** |
| It stopped being theirs (reporting line changed, HR scope changed) | It is gone from the list. Nothing is said, because saying "you no longer approve for Rakesh" leaks an org change through a notification. |

**Risk to write into the spec.** A merged page that fetches both feeds on open is a
snapshot. Today's Home card already has this (`HM_STALE_MS = 60000`, and
`hmDropPending` removes a row locally after a decision). The notifications page must
reuse both, not invent a third freshness rule.

---

## 6 · Filters — the smallest set that is actually useful

**Recommendation: three chips in one row, mutually exclusive, no combinations.**

| Chip | Shows | Why it earns its place |
|---|---|---|
| **All** (default) | tasks group · notices group · "waiting on someone else" group | One place, as the ticket asks |
| **To do** | the tasks group only | The manager's and the frontline worker's actual question. One tap from the bell to a pure work list |
| **Unread notices** | unread notices only | The only *volume* problem we actually have: unread notices never expire (`notices.py` keeps them whatever their age), so this list grows for ever while tasks do not |

Three short words wrap safely at 360 px and at 200 % text, and **nothing is ever greyed
out** — each chip is a whole intent, so there is no invalid combination to disable.
(Mutually exclusive is the point: "Unread" as a *toggle* would have to be disabled under
"To do", because a task has no read state — and a greyed control that does not say why is
on our anti-pattern list twice.)

**Deliberately not proposed, and why:**

| Left out | Why |
|---|---|
| A filter per kind (leave · expense · goal · attendance · policy) | Six more controls for a list that is capped at 50 per kind and usually has single digits. "To do" plus oldest-first ordering already answers it. If an HR person ever needs leave-only, the Team page is the leave screen |
| Date range, month picker | There are only 30 days of read notices and no archive behind them. A date filter over 30 days is furniture |
| Search | No index, no archive, and nothing to search but 300-character sentences |
| Sort order control | One correct order exists: oldest-waiting first for tasks, unread-then-newest for notices. A sort control invites a person to choose a worse order |
| "Sender" filter | One tenant has a handful of senders |
| Read / unread toggle **per row** | We have no "mark unread", and adding one invites people to hide a notice from themselves |
| Unread-only for **tasks** | A task has no read state (§5.2) |
| Saved filters / views (Workday) | §4, "what we will not copy" |
| A count on each chip ("To do 4") | The group heading already carries the number, and a count inside a filter control is the trap `ux-learnings` records: a total beside a filter that is not the filtered total |

⚠ **DECISION 1.** Three chips, or four (adding plain **"Notices"** so read ones are
reachable without "All")? My recommendation is **three** — "All" already reaches read
notices, and a fourth chip is the first step to eight. I have low confidence here; it
is cheap to change and worth one question in a usability session (§8).

---

## 7 · Ideas, persona by persona

Each row says the job it serves and the evidence. The PM decides what enters the slice.

### 7.1 Employee — the persona the ticket is for

| Idea | The job it serves | Evidence | Size |
|---|---|---|---|
| **The bell on every screen on a laptop**, in Frappe's navbar at the right, immediately left of the existing post-login avatar menu, with the word **"Notices"** as its accessible name (already correct: `ntPaintBadge` writes "Notices, 3 unread") | "Is anything waiting?" answered without going to Home | S3 in §2.1: no bell exists above 768 px. Top-right is where all six benchmarked products put it | S |
| **A real page, with an address and a sidebar entry**, replacing the slide-up sheet as the "see all" destination | A thing you can bookmark, reload, come Back to, and be sent a link to | F2 and F1 in §2.4 — without a nav item the page cannot survive a reload | M |
| **"Mark all as read" in the notices group** | 20 unread = 60 taps today | NC2 | S |
| **Say when the list was cut**: "Showing the first 100" | `READ_CAP` truncates silently while the sibling endpoint carries `capped` for exactly this | NC1 | S |
| **"Waiting on someone else"** as a third, uncounted group | "Where has my leave request got to?" has no home today except the Leave page | `my_requests` already returns `state`, `says` and `can_withdraw` | S |

**What changes for them if we get it wrong:** a badge that will not go to zero. That is
the one-way rule (product-context §2) in this slice: we must not make a manager's
overview cheaper by giving an employee a number they cannot clear.

### 7.2 Frontline employee on a shared factory handset — the hardest case

DTC has **441 staff logins on shared handsets** (`frame.html`, ALV-222 comment). Nothing
here may assume a personal phone.

| Idea | The job it serves | Evidence | Size |
|---|---|---|---|
| **Nothing about notices may be written to `localStorage` or `sessionStorage`** | The next person on the handset starts clean | The portal already keeps exactly one thing (`sb-pinned`) and clears it on **both** doors out. A cached notices list would be the second thing, and the first one containing another person's HR messages | S (a rule, not code) |
| **The page must render nothing from cache after sign-out** — test Back after `/logout` | A 30-day list of one person's HR messages on a shared device is a privacy surface, not a convenience | New risk created by this slice: today's sheet is transient; a *page* invites Back | S to test, must be an AC |
| **Keep the badge the only thing they must read.** One number, 44 px target, word beside it | Two minutes on a phone (nfr-budget §7) | `.mob-notif` is already boxed to 44 px at ≤768 px (`frame.css:353`) | — (Keep) |
| **A fourth bottom-bar item is *not* the answer** | The bar has three items (Home · Attendance · Finances) and room for a fourth, but the bell is already in the top bar one thumb away; two doors to one place is the duplicate trap `ux-learnings` warns about | `parts/drawers.html:67` | — (do not build) |
| **Hindi first.** Three chips and two group headings is ~5 new strings; Devanagari runs ~30 % longer | Their own language (product-context §2) | `drT()` already wraps every string in this block | S |

### 7.3 Line manager — the biggest single gain in the slice

| Idea | The job it serves | Evidence | Size |
|---|---|---|---|
| **A pending approval visible in the bell, from any screen, on a laptop** | A manager between meetings does not visit Home. Today their only global signal is a sidebar badge that appears *after* they open the panel (S4–S8) | §2.1. Keka shipped its bell for exactly this reason: items were *"waiting to surface in the Inbox"* (§4) | — (this is the merge) |
| **Approve and decline from the page**, reusing `hmLeaveSheet` / `hmExpenseSheet` unchanged | One action, not a routing journey (product-context §2) | The sheets exist, carry Approve/Decline-with-a-reason, and already drop the row locally on success | S — reuse |
| **Oldest-waiting first, with the waiting line in words** ("waiting 4 days") | Exceptions before lists | `waiting_since` and `hmWaiting()` already exist | — (Keep) |

### 7.4 HR Manager

| Idea | The job it serves | Evidence | Size |
|---|---|---|---|
| **The same page, no HR variant** | One screen to explain to 441 people and to themselves | Scope is already per-part inside `get_inbox`; HR simply sees more rows | — |
| **A capped group must say it is capped** | HR is the only persona who will hit `LIST_CAP = 50` and `READ_CAP = 100` | NC1 | S |
| ⚠ Not in this slice: **did my announcement land?** | A sender's real question | `Notification Log.read` would answer it, and reading it per recipient is read-tracking of named colleagues — a privacy decision, not a layout one. Flagging, not proposing (⚠ DECISION 4) | — |

### 7.5 CXO / founder

| Idea | The job it serves | Evidence | Size |
|---|---|---|---|
| **The CXO's badge counts kinds, not rows** — or is suppressed above a threshold | A company-wide approval count can be in the hundreds; a badge reading "214" on a five-minute phone check is noise, not information | `hmPaintPending` already sums *kinds* for a CXO (`hmIsCxo`) and the Home chip already differs for them. The badge would be the only place that does not | S, but needs ⚠ DECISION 2 |
| **The page keeps the per-kind rows for a CXO** | "Counts by kind. Tap one to open its screen." already exists and works | `HM_KIND`, `hmPendAll` | — (Keep) |

---

## 8 · Accessibility, privacy and honest states — what the design step must carry

**Accessibility (WCAG 2.2 AA, nfr-budget §7).**

- The badge is **11 px on a laptop** (§0, NB3). Floor is 12 px.
- Colour is not the only signal: the badge is red (`--red`) and the only other cue is the
  digit. "Red is for overdue or wrong, never for an ordinary count" is our own rule —
  and a notice count is an ordinary count. ⚠ **DECISION 3**: badge colour. My
  recommendation: `--primary` for an ordinary count, and keep red for nothing, since we
  have no overdue concept here.
- The badge sits **inside** the 32 px circle at `top:2px;right:2px`, overlapping the bell
  glyph. Our own checklist says badges sit outside the icon (NB5).
- On desktop the target floor is **24 px** (not 44 px). A 32 px bell passes.
- Three chips must be a real radio group or a set of `<button aria-pressed>`, keyboard
  reachable, focus visible. The existing `.bnav-item` and the chart cards show this
  project's habit of `onclick` on a `<div>`; do not repeat it.
- The page replaces an overlay, which removes two problems for free: no focus trap, no
  Escape handling, no "return focus to the opener" (`HM.opener`).
- Test at 200 % text (= 195 CSS px of room on a 390 px phone) and at 360 px.

**Privacy.**

- Every row of both feeds is already scoped server-side (K2). **Flag per the data-doors
  rule: this page shows no other person's data beyond what the approver is deciding** —
  a name, a leave type, dates, an amount. That is `ROW_KEYS`, unchanged. **No absence
  reason anywhere.** The slice adds no field.
- The slice *does* create one new exposure: a durable, addressable page holding 30 days of
  one person's HR messages, on shared handsets. See §7.2 — two ACs, not a design change.
- No personal data in any error the page shows.

**Honest states the design step must draw** (none exist for this page today):

loading (skeleton within 300 ms, nfr-budget §2) · empty-all ("Nothing waiting on you,
and no new notices") · empty-tasks-only · empty-notices-only · first-time (a new joiner
on their first morning: both groups empty — say what the page is *for*) · one feed loaded,
the other failed (**draw what you have**, say which part is missing, offer Try again —
do not fail the whole page) · both failed · timeout with an end ("Try again", never an
endless spinner) · stale row refused (§5.3) · capped list · 100 unread · offline ·
signed-out-then-Back.

---

## 9 · Findings, with severity

| ID | Finding | Impact | Kind | Size | Severity | Evidence |
|---|---|---|---|---|---|---|
| **NB1** | No bell above 768 px, so a laptop user has no global "something is waiting" signal | High | Fix | S | **P2** | `frame.css:231` + `panels.css:367` |
| **NB2** | The badge has two boot paths: `homeNotices` paints it on Home, and `ntBellBoot` runs on a **1,500 ms `setTimeout`** elsewhere and early-returns if Home already answered. So off Home the badge appears up to 1.5 s late, with no skeleton | Medium | Fix | S | **P3** | `portal.js:18393`, `6835` |
| **NB3** | Badge text is `--fs-xs` = **11 px on desktop** (12 px only under `@media(max-width:768px)`), below our 12 px floor. Fix in `.notif-badge`, **not** in the shared token — `design_system.html` is included by 7 pages | Medium | Fix | S | **P2** | `panels.css:1482`, `design_system.html:11`, `frame.css:332` |
| **NB4** | Badge is red (`--red`) for an ordinary count, against our own rule, and colour is close to its only signal | Low | Improve | S | P3 | `panels.css:1482` |
| **NB5** | Badge is inside the icon, overlapping the glyph; our checklist says outside | Low | Improve | S | P4 | `panels.css:1482` |
| **NP1** | A panel with no visible nav item cannot be deep-linked or restored — reload and Back both drop to Home | High | New | S | **P2** | `mayOpenPanel`, `portal.js:4707` |
| **NC1** | `READ_CAP = 100` truncates silently; `notices_feed` returns no `capped` key, while its sibling `get_nav_counts` carries `cap` and `capped` for exactly this purpose | Medium | Fix | S | P3 | `notices.py:41`, `inbox_api.py:1143` |
| **NC2** | No "mark all as read". 20 unread ≈ 60 taps | Medium | New | S | P3 | `ntOpenAll`, `ntOpenOne` |
| **NC3** | A **read** notice older than 30 days is unreachable by any route. Correct for now (K6, matches Workday) but it must be *said*, not discovered | Low | Improve | S | P4 | `notices.py:41` |
| **NC4** | The sender is `from.split(",")[0]` on a row and the full `from` in the detail sheet — one idea in two forms | Low | Fix | S | P4 | `ntRowHtml` vs `ntOpenOne` |
| **NX1** | Five sidebar badges come from five different calls and appear only after the person opens that panel, while `get_nav_counts` — one filter per part, tested — has no caller on the live portal | Medium | — | M | P3, **out of this slice** | §2.1 |
| **NX2** | **I saw nothing in a browser.** Docker is not running, so there is no bench. Every measurement above is computed from CSS tokens | — | — | — | **blocks confidence, not the brief** | `docker ps` failed, 6 Nov 2026 |
| **K1–K8** | §2.3 — keep every one | — | Keep | — | — | §2.3 |

**Nothing here is P0 or P1.** The slice is not a release risk as scanned; the two P2 items
(NB3, NP1) are both one-line structural choices made before any code is written, and
NB1 is the ticket itself.

---

## 10 · A usability test plan for the High-impact items

Five people, 10 minutes each, on their own device, no training.

| Who | Task | Success | What would change the design |
|---|---|---|---|
| 2 × frontline, shared Android, Hindi | "Something is waiting for you. Deal with it." | Reaches the right item from the bell in **under 2 minutes**, first try | If they open "All" and scroll past tasks to notices, the page opens on **To do** instead |
| 1 × line manager, laptop | "Approve anything your team is waiting on." Then: "Is there anything else waiting?" | Approves from the page; then says the badge went from 7 to 6 and can say why | If they expect the badge to drop when they *read* the page, D is wrong and we fall back to A (two numbers) |
| 1 × employee | "Where has your leave request got to?" | Finds it under "Waiting on someone else" | If they look for it under "To do", the third group needs a different name |
| 1 × HR | "Clear your notices." Then: "What is this number counting?" | Uses Mark all as read; explains the badge in one sentence without being told | If they cannot explain the badge, the group headings are not doing their job |

**The one question I would most want answered:** does a merged badge make people trust
it more, or less? That is the whole bet in §5.1.

---

## 11 · Subtract pass

Read once more asking only *what can I delete?* **Removed:**

- **A merged server endpoint.** Two existing calls, no third filter (§3).
- **A per-task "seen" flag**, and with it a Custom Field, a DocType and a migration
  (§3, §5.2). This is the single biggest deletion in the scan.
- **Tabs.** Three chips over two stacked groups does the same job with less chrome than
  Gusto's or Keka's tabs, and keeps "All" possible.
- **A fourth bottom-bar item on the phone** (§7.2).
- **Per-kind filters, date range, search, sort control, sender filter, saved views,
  per-chip counts, per-row read toggles** — eight controls, all named in §6 with reasons.
- **Fixing the five stale sidebar badges** — real, recorded as NX1, explicitly not in
  this slice.
- **Read-tracking for announcement senders** — recorded as ⚠ DECISION 4, not designed.
- **Push, sound and browser permission prompts** (§4).
- **A dismiss / snooze / mark-done control on a task row** (§5.3).

**Kept despite the pass, each with a named reason:** the sidebar nav item (F1 — without
it the page is not a page), "Mark all as read" (NC2 — 60 taps), the "capped" line
(NC1 — the sibling endpoint already sets the standard), the third uncounted group
(nothing else answers "where is my request?").

---

## 12 · Open questions

| # | Decision needed | Why it matters | Owner | Blocks | My recommendation |
|---|---|---|---|---|---|
| ⚠ 1 | Three chips (All · To do · Unread notices) or four (add Notices)? | Four is the first step to eight; three may hide read notices behind "All" | `hrms-product-manager`, with Surbhi | The page's controls | Three. Low confidence; test it (§10) |
| ⚠ 2 | For a **CXO**, does the badge count rows or kinds — or is it suppressed above, say, 99? | A badge reading "214" on a five-minute phone check is noise. Home already treats a CXO differently; the badge would be the only place that does not | Surbhi | The badge rule | Count **kinds** for a CXO, matching Home |
| ⚠ 3 | Badge colour: red, or `--primary`? | Red for an ordinary count breaks our own rule and is on the anti-pattern list twice | Surbhi | One CSS line | `--primary`. Keep red for nothing on this page |
| ⚠ 4 | **⚠ COMPLIANCE** — may an announcement sender see **who has read** their notice? | `Notification Log.read` makes it trivial, and it is read-tracking of named colleagues. Not asked for in ALV-322 | `hrms-security-privacy-engineer`, then Surbhi | Nothing in this slice — but it will be asked for | Out of scope. Decide it in its own slice, with counsel |
| ⚠ 5 | Do the five per-panel sidebar badges (NX1) get replaced by `get_nav_counts` with the bell, or left alone? | A trustworthy bell makes five stale badges more visibly wrong | `hrms-product-manager` | Scope only | Leave them. Record as a separate line |
| ⚠ 6 | Where exactly does the desktop bell go: **Frappe's navbar** (right end, left of the avatar menu) or the **sidebar footer**? | The navbar is Frappe's template, though the portal already overrides its brand and hides two of its items; the sidebar footer is ours but is bottom-left and collapses to icon-only | `hrms-fullstack-engineer` on feasibility, then Surbhi | The bell's position | **The navbar.** It is already treated as our desktop top bar (F2), and top-right is where every benchmarked product puts a bell |

---

## 13 · Assumptions

- `[ASSUMPTION]` `get_inbox` and `notices_feed` each answer inside the ≤ 500 ms p95
  whitelisted-call budget on a warm frame at DTC's ~600 staff. Measurement scripts exist
  (`tests/measure_076.py`) and were **not run** — no bench (NX2). The engineer should run
  them before the strategy gate.
- `[ASSUMPTION]` Most employees have single-digit unread notices and single-digit tasks,
  so the page needs no pagination beyond the existing caps. **Unverified** — I could not
  count `Notification Log` rows per user at PPJ or DTC. If the real number is in the
  hundreds, "Unread notices" stops being a filter and becomes the main view, and §6
  changes.
- `[ASSUMPTION]` The frontline worker reaches the portal in a browser, not a native
  shell, so there is no OS notification tray in play (mobile is a PWA — user's own
  decision, 24 Oct 2026).
- `[ASSUMPTION]` Adding one button to Frappe's website navbar is low-risk because the
  portal already rewrites its brand text and hides two of its menu items. Engineer to
  confirm (⚠ 6).
- `[recall — verify]` Frappe Desk's own notification dropdown and its tabs. Not
  load-bearing: the relevant fact is that nothing ships for the **website** side.
- Competitor rows are labelled individually in §4. Keka's and Gusto's help centres
  returned 403 to a direct fetch; Darwinbox's own help pages were not found at all.

---

## 14 · Handoff note — to `hrms-product-manager`

**The layout is the easy half. The number is the brief.** Showing the bell on a laptop
and turning a sheet into a page are both front-end work on two endpoints that already
exist — rung 4, no server change, no DocType (§3). What needs your decision is §5: a
single merged badge defined as **unread notices + approvals waiting on me + policies to
acknowledge**, deliberately **excluding my own pending requests**, with the Home
"Pending for you" card kept as a named subset. If you take that, three rules travel with
it into the spec and must not be softened: **tapping a task navigates and marks
nothing** (§5.2); **a task never leaves the list unless the work was done or someone
else did it, and a stale tap says which** (§5.3); and **nothing about notices is cached
in the browser, because 441 DTC logins share handsets** (§7.2).

**I disagree with one implicit part of the ticket.** "Merge the two feeds" reads as *one
list*. I am recommending **one place with two visibly different groups**, because five of
the six products I could check keep news and tasks apart, and the one that merged the
read state (Zoho People) has users saying out loud that they can no longer tell whether
the work got done. If Surbhi wants a single undifferentiated list, say so at the brief
gate and I will design it — but the badge then cannot be trusted, and I would want that
written down.

**Six decisions are open (§12); ⚠ 2, ⚠ 3 and ⚠ 6 are small and ⚠ 4 is a compliance
question I have deliberately left out of scope.** Two P2 findings (NB3, the 11 px badge;
NP1, a page with no nav item cannot be reloaded) are cheap now and expensive after the
markup is written — put both in the brief rather than leaving them to the design step.
And please carry NX2 forward: **nothing in this scan was seen in a browser**, because
Docker was not running. The design step needs a bench.
