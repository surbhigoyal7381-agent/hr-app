---
slice: 083-ess-notifications
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-11-06
status: draft — for Surbhi's decision at the brief gate
inputs: [01a-ux-opportunities.md, 07-devops-inputs.md (§1), .claude/context/data-doors.md, .claude/context/no-over-engineering.md, .claude/context/product-context.md, .claude/context/handoff-contract.md, docs/product/priorities/2026-09-29-backlog-groom.md, docs/slices/076-home-notices/01-product-brief.md, notices.py, inbox_api.py, portal.js, frame.css]
ticket: ALV-322 (Epic, ALV project)
---

# 083 · A notifications bell and page on the employee portal — product brief

## Bad news first, three things

1. **The badge number is the whole brief. The bell is trivial.** Showing the bell on a
   laptop is half a day of markup and CSS (DevOps §5, Estimate). What takes thought is
   what the number counts. Get it wrong and we ship an employee a number they can never
   clear — which fails product-context §2's one-way rule, and would be the worst possible
   outcome of a slice whose whole point is to reduce anxiety about what is waiting.

2. **The designer's badge definition is not free, and nobody has said so yet.**
   They propose excluding the person's own pending requests (`my_requests`) from the
   badge. **Confirmed in code:** today's Home "Pending for you" chip *includes* them
   (`hmPaintPending`, `portal.js:6655`, total = `d.total − shift_requests`, and
   `d.total = approvals + policies + my_requests`, `inbox_api.py:1132`). So excluding
   them means **changing a number already shipped in slice 076**, or living with a bell
   and a Home chip that disagree. I recommend changing Home. It is small, but it is a
   change to a live surface and it is Surbhi's call (⚠ DECISION PM-2).

3. **One more code-level correction to carry into the spec.** `approvals_total`
   **includes shift requests** (`APPROVAL_PARTS`, `inbox_api.py:88`). So the badge cannot
   be `approvals_total` minus anything hand-waved — it must be summed from the `parts[]`
   counts, skipping `shift_requests`, exactly as Home already does. **Confirmed**, read
   today.

**Not in the 29 Sep 2026 priorities review.** I grepped it: no mention of a bell, a
notification or the inbox. **This is new scope.** It arrived as a direct customer-facing
request and I am classifying it below from proxies, not from survey data.

---

## 1 · Job to be done

> *"we need to add notifications bell icon on the employee self service portal as well and
> it would redirect to a page which shows all notifications with a few filters."*
> — Surbhi, 6 Nov 2026 (**Confirmed**, her words, ALV-322)

In the user's own words, the job underneath it:

> **"When I am anywhere in the portal, I want to know whether anything is waiting for me
> and go straight to it, without going Home first and without being told twice."**

**Primary persona: Employee** (own company, mostly own record). **Biggest single gain:
the line manager**, who is also an employee here — they are between meetings on a laptop
and today get no global signal at all (`.mob-header{display:none}`, `frame.css:231`,
**Confirmed** by reading the file).

What changes for the other two:

- **HR Manager** — the same page, no HR variant. They see more rows because
  `get_inbox`'s scope is already per-part. They are the only persona who will hit the
  row caps, so the page must say when a list was cut.
- **CXO** — the page keeps Home's existing CXO shape: one row per kind with a count, no
  400 names (`HM_KIND`, **Confirmed**). Their badge needs a decision (⚠ DECISION PM-4).

**Nobody is quietly harmed** — on one condition: the badge must be a number the holder
can get to zero by doing work. That condition is §8.

---

## 2 · Current pain — a story, because I have no number

**I have no usage data. Nothing counts portal page views and nothing counts notices per
person.** (DevOps §7 says the same; the 6,400 page views/day figure in §1 is their
Estimate from headcount, not a measurement.) So, a concrete story instead.

A DTC line manager opens the portal on their laptop at 09:20 to check their own
attendance. Four leave applications are waiting on them. The portal shows them nothing.
No bell exists above 768 px. The Leave sidebar badge only paints *after* they open the
Leave panel (`portal.js:9441`, **Confirmed** via the designer's S4–S8 table). They close
the tab. At 16:00 a supervisor phones them because the line is short tomorrow.

On a shared factory handset the same manager *does* get a number — but it counts notices
only, so it is silent about the four approvals. **The bell today answers a question
nobody asked.**

**Evidence required** (not blocking): how many non-Home portal pages a DTC manager opens
in a day, and how many unread notices a typical DTC employee carries. Both are a
read-only count on the tenant and would sharpen §12's baselines.

---

## 3 · Competitive analysis — whole products

The designer's benchmark (01a §4) is the evidence base; every row there is labelled and
I am not re-labelling it. My addition is the product lens.

| Capability | Workday | Keka | Zoho People | BambooHR | greytHR | Gusto | **Alvora today** |
|---|---|---|---|---|---|---|---|
| Bell, with a count | yes | yes (new) | yes `[recall — verify]` | inbox icon, not a bell | yes ("Message Center") | yes | **phone only** |
| What the bell holds | news only, stated explicitly | time-sensitive alerts | news + tasks, one read state | — | bulletin, payslips, letters | two tabs: Tasks, Activity | notices only |
| Work owed lives | "My Tasks", separate | "Inbox" + "Take Action" tab | approvals inbox `[recall — verify]` | "Needs Your Attention" on Home | "To Do > Tasks" | same bell, other tab | Home card only |
| Home surface **as well** | yes | yes | yes | yes | yes | yes | yes |
| Filters | on My Tasks, a builder | tabs | not found | per-category on/off | Open/closed | two tabs | **none** |

**Pricing and packaging lens — and I am honest that this is weak evidence.**
`[ASSUMPTION]` In all six, notifications sit in the **base tier** and are never sold as
an add-on; I found no vendor pricing page naming notifications as a paid feature and I
did not open a pricing page in this run. **Evidence required** if anyone wants to lean on
it. The product consequence, if true, is the important part: **a bell earns no money and
wins no deal. Its absence loses one.** That is the definition of a Must-be, and it is why
this slice should be small and then finished.

### What we will deliberately NOT do, though they all do it

| Not doing | Why it makes us better for *our* user |
|---|---|
| **Tabs** (Gusto, Keka) | Two stacked groups with headings on one page means the frontline worker on a 360 px screen never has to find the right tab before finding their work. One scroll, no navigation. |
| **A filter builder** (Workday) | Our HR person is one person with tens of rows. A builder is a surface to maintain for nobody. Three chips. |
| **Per-category "don't show me this"** (BambooHR) | It lets a manager switch off the category their colleagues are waiting in. Our answer to "I don't want to see this" is *do the work*. |
| **A sound and a browser-permission prompt** (Keka) | A sound belongs to whoever is holding the shared handset. Push is its own slice, or never. |
| **Reading a task marks it read** (Zoho People) | Their own users say they can no longer tell whether the work got done (01a §4, read 6 Nov 2026). We refuse to ship a badge that goes quiet without the work happening. |
| **A widget that hides itself when empty** (BambooHR) | "Nothing waiting on you" teaches people the surface is trustworthy. A card that only appears with bad news trains dread. |
| **An "all notifications ever" archive or search** | We have neither an index nor an archive. Promising history we cannot serve is worse than saying "Last 30 days". |

---

## 3a · Three ways to solve it

| Approach | What it is | Verdict |
|---|---|---|
| **Conventional** | A new `/notifications` web page, a new merged `notifications_feed` endpoint with server-side filters and paging, a per-task "seen" flag so the bell can be cleared | **Rejected.** It needs an nginx change on the one file that serves production (DevOps §4, P1), a third filter expression over data two endpoints already answer, and a new Custom Field for "seen". Roughly triple the days for no extra user outcome. |
| **Better — recommended** | A hash route inside `/hrms-employee`, two calls that already exist, filters in the browser, three chips, two counted groups plus one uncounted group, bell shown on desktop by moving markup | **Recommended.** Rung 4, front end only, zero new server code, zero new infrastructure, ₹0 extra run cost. |
| **Reimagined** | Push / WhatsApp: tell the person on their phone before they open the portal | **Rejected for now, and it is genuinely interesting.** 441 DTC logins share handsets, so a push reaches the wrong hands. WhatsApp is a separate product decision with its own cost and consent story. Record it; do not start it here. |

**Could we not build this at all?** Partly, and it is worth saying out loud: **part 1 alone
is almost "not building it".** The bell markup is already rendered on desktop and the call
already runs there (DevOps §1, **Fact**). One CSS line hides it. Half a day gets a laptop
user a global signal. If Surbhi wanted the cheapest thing that answers her sentence's
*first* clause, that is it, today. I am not recommending stopping there, because the bell
would still be silent about approvals — which is the actual pain in §2.

---

## 4 · Kano class and demand

**Proxy classification. No survey data. Marked `proxy` honestly.**

| Part | Class | Why (proxy rule) | Evidence | What would change it |
|---|---|---|---|---|
| **1 · Bell on desktop** | **Must-be (proxy)** | All six benchmarked products ship a global notification affordance, and the customer asked for it unprompted | all six: read 6 Nov 2026 (01a §4). The ask: **seen** — Surbhi, 6 Nov 2026 | A survey showing employees never look for it. Unlikely. |
| **2 · A page with filters** | **Performance (proxy)** | Buyers compare "how good is the inbox"; more reachable notices is better, fewer is worse. Our own "cannot reach a read notice past 30 days, no mark-all-read, 60 taps for 20 notices" is a quality gap, not an absence | 01a §2.2 (read from code, 6 Nov 2026) | If a typical employee carries 2 unread notices, filters are Indifferent and the page should shrink to a plain list. **This is the assumption I would most like tested.** |
| **3 · Approvals in the bell** | **Performance (proxy), close to Must-be for a manager** | Five of six separate the two surfaces but **every one of them makes work owed globally visible somewhere**. Keka shipped its bell for exactly this ("without waiting for them to surface in the Inbox") | 01a §4, read 6 Nov 2026 | A manager saying the Home card is enough. Testable in §10 of 01a. |
| **A flat merged list where reading clears work** | **Reverse (proxy)** | It trades a true signal for a tidy one. Zoho People's users complain about precisely this | 01a §4, read 6 Nov 2026 | Nothing I can imagine. This is the one shape I will argue against. |
| **A badge counting the person's own pending requests** | **Reverse (proxy), mildly** | A number the holder cannot reduce by acting. It nags and teaches people to ignore the badge | reasoning, not evidence — `[ASSUMPTION]` | A usability session where employees say they *want* their own requests counted. Worth one question. |

**Demand evidence, all of it:**

- **seen** — Surbhi's own request, 6 Nov 2026, raised as Epic ALV-322.
- **read** — six competitor products, 6 Nov 2026, via the designer's benchmark; two
  help centres returned 403 and Darwinbox's own pages were not found.
- **Not** in the 29 Sep 2026 priorities review (**Confirmed** by grep). No customer
  ticket, no lost deal, no demo note behind this. One customer voice, strongly held.

**Kano drift note:** a bell is 2026's furniture, not 2026's delighter. Treat it as
plumbing: build it, finish it, do not polish it.

---

## 5 · Persona enhancements through the portal — what is in, what is not

Every idea from 01a §7, decided.

| # | Persona | The portal enhancement | The job it serves | In this slice? | Why |
|---|---|---|---|---|---|
| 1 | Employee | **Bell visible on a laptop**, top-right in Frappe's navbar | "Is anything waiting?" from any screen | **Yes** | The ticket. 0.5 day, no run cost. |
| 2 | Employee | **A real page with an address and a sidebar entry** replacing the sheet as "see all" | Bookmark it, reload it, come Back to it | **Yes** | The ticket, and without the nav item the page cannot survive a reload (`mayOpenPanel`, `portal.js:4707`). |
| 3 | Employee | **Three filter chips** — All · To do · Unread notices | "Just show me my work" | **Yes** | The ticket says "a few filters". Three is the fewest that is useful. |
| 4 | Employee | **"Mark all as read", notices group only** | 20 unread ≈ 60 taps today | **Yes** | Cheap, and the page is otherwise a worse place to clear a backlog than the sheet it replaces. |
| 5 | Employee | **Say when the list was cut** — "Showing the first 100" | Not mistaking a slice for everything | **Yes** | `READ_CAP = 100` truncates silently (**Confirmed**, `notices.py:42`) while the sibling endpoint already carries `capped`. Two lines in an existing return. |
| 6 | Employee | **"Waiting on someone else"** as a third, **uncounted** group | "Where has my leave request got to?" | **Yes** | These rows already come back in the same call and already appear on Home, unlabelled. Giving them a heading costs nothing and is what lets us take them out of the count. |
| 7 | Employee | **Say "Last 30 days"** on the page | Not promising history we do not keep | **Yes** | One string. Workday does the same (01a §4). |
| 8 | Frontline, shared handset | **Nothing in `localStorage` or `sessionStorage`; Back after `/logout` renders nothing** | The next person on the handset starts clean | **Yes — two acceptance criteria, not design** | This slice's one new exposure. See §9. |
| 9 | Frontline | **Hindi at parity** — ~5 new strings | Their own language (product-context §2) | **Yes** | `drT()` already wraps this block. |
| 10 | Line manager | **Approvals visible in the bell from any screen** | The pain in §2 | **Yes** | This is part 3. 0.5–1 day, +638 B per page. |
| 11 | Line manager | **Approve and decline on the page**, reusing `hmLeaveSheet` / `hmExpenseSheet` unchanged | Act where you see the problem | **Yes — reuse only** | The sheets exist and already drop the row on success. If the engineer finds the reuse is not clean, drop it to "later" rather than writing a new sheet. |
| 12 | CXO | **Badge counts kinds, not rows** (or is capped at 99+) | A badge reading "214" is noise | **Yes, subject to ⚠ DECISION PM-4** | Home already treats a CXO differently; the badge would be the only place that does not. |
| 13 | HR Manager | **One page, no HR variant** | One screen to explain to 441 people | **Yes** | Scope is already per-part server-side. |
| 14 | HR Manager | **Did my announcement land — who read it?** | A sender's real question | **No — out of scope** | ⚠ COMPLIANCE. Read-tracking named colleagues. Security decides, in its own slice. See §10. |
| 15 | All | **Fix the five stale sidebar badges with `get_nav_counts`** (NX1) | Numbers that are true before you click | **No — separate slice** | §7 gives my reasoning. |
| 16 | Frontline | **A fourth bottom-bar item for notifications** | — | **No** | Two doors to one place. The bell is a thumb away in the top bar. |
| 17 | All | **Push / sound / browser permission prompt** | — | **No** | Shared handsets. Its own slice or never. |
| 18 | All | **A per-task "seen" flag so the bell can be quietened** | — | **No, and never** | It is the Zoho People failure, and it is rung 5 of the ladder for a behaviour nobody asked for. |

---

## 6 · The WOW

**One moment. The manager, on a laptop, on any screen that is not Home.**

They are on their own Attendance page. Top-right, in the navbar they have looked at a
hundred times, a bell now carries **7**. They click it. The page opens with no tab to
choose, and the first heading reads:

> **4 waiting on you**
> Leave · Rakesh Kumar · 12–14 Nov · *waiting 4 days*   **Open**

They approve two from that page without going anywhere else. The badge goes to **5**, and
the group heading to **2 waiting on you**, as they watch.

Below it, the second heading:

> **3 unread notices**  ·  *Mark all as read*

That is the whole WOW: **the number went down because they did the work, and they could
see exactly which part of it moved.** It is achievable inside this slice — the decision
sheets already exist and already decrement the count (`hmDropPending`, `portal.js:6799`,
**Confirmed** via DevOps §2).

Micro-copy to carry into the spec (English; Hindi at parity): `4 waiting on you` ·
`3 unread notices` · `Waiting on someone else` · `All` · `To do` · `Unread notices` ·
`Mark all as read` · `Last 30 days` · `Showing the first 100` ·
`Nothing waiting on you, and no new notices.` · `Already decided by someone else.` ·
`The request was withdrawn.`

---

## 7 · The thin slice

**All three parts are in, and the slice stands alone without a phase 2.** I checked that
honestly: if we stop after it ships, nothing is half-built and no screen says "coming
soon". Total DevOps Estimate: **2–3 engineering days**, no new infrastructure, ₹0 run cost.

**In scope**

1. The bell on desktop (part 1).
2. A notifications **hash route** inside `/hrms-employee`, with three chips, two counted
   groups and one uncounted group, "Last 30 days", a capped line, "Mark all as read",
   and a sidebar nav item so it survives a reload (part 2).
3. The badge counts notices **and** work owed, per §8 (part 3).
4. Fix the 11 px badge in `.notif-badge` only — not in the shared token (NB3, P2).
5. The two shared-handset acceptance criteria (§9).

### The four piles

| Pile | Items |
|---|---|
| **Needed to validate this now** | The desktop bell; the page; the merged badge with the §8 definition; the three chips; the group headings. |
| **Needed before it can ship** | The 12 px badge floor; Hindi strings; the two shared-handset ACs; the stale-row messages ("Already decided by someone else", "The request was withdrawn"); the "Last 30 days" and capped lines; failing silently on either call (DevOps OPS-6); the disjoint-sets test (OPS-8); the data-doors door list on Notification Log as a plain staff login (OPS-10). |
| **Worth doing later** | Replacing the five stale sidebar badges with `get_nav_counts` (NX1 / ⚠ 5); a fourth chip for read notices; the `_dtc_row_facts` flatness test (OPS-7, pre-existing); `_my_employee` asked twice; push or WhatsApp. |
| **Not doing** | A per-task "seen" flag; any dismiss, snooze, swipe-away or mark-done on a task row; tabs; a merged server endpoint; a new web page; search; date range; sort control; sender filter; per-kind filters; saved views; per-chip counts; per-row read toggles; a badge cache; a fourth bottom-bar item; sound and push prompts; announcement read-tracking. |

**On the five stale sidebar badges (⚠ 5): leave them. I agree with Surbhi's instinct —
separate slice.** My reasons: it changes five live surfaces for a quality problem no
customer has reported; `get_nav_counts` has never been measured in DTC's actual
configuration (DevOps OPS-3), so wiring it to five badges on top of the bell multiplies
an unmeasured risk; and it is scope creep by the plain definition in
`no-over-engineering.md` §6. **But say it out loud:** after this slice the bell will be
visibly more trustworthy than those five badges, and somebody will notice. Record it as
its own line.

### Out of scope, stated plainly

The sender's side of announcements · who read an announcement · push, email, SMS,
WhatsApp · the Desk · any new field, DocType or app · any change to what a row contains
(`ROW_KEYS` unchanged) · pay, health or passport data (this slice touches none).

---

## 8 · The number — the one product decision

**The outcome I am protecting:** *a person should be able to look at one number, trust
it, act, and watch it fall to zero.* Everything below follows from that sentence.

### 8.1 One place, two visible groups — not one flat list

**I agree with the designer, and I am recommending it as the product shape, not as a
layout.** "Merge the two feeds" as a single undifferentiated list fails the outcome above,
because the two kinds of row have different end states. A notice ends when it is **read**.
An approval ends when it is **decided**. A list that treats them the same has to pick one
end state, and whichever it picks, half the rows lie.

| Shape | What the user gets | Verdict |
|---|---|---|
| One flat list, reading clears everything | A tidy badge that goes quiet while four people wait for leave | **Recommend against.** Reverse (proxy). Zoho People shipped it; their users complain. |
| One flat list, nothing ever clears | A badge that only falls when work is done — honest, but the person cannot tell *why* it is 7, or which rows they can clear by reading | Workable but worse. Loses the WOW in §6. |
| **One page, two counted groups, one uncounted group** ✅ | One badge; "4 waiting on you" and "3 unread notices" reconcile it in words on screen | **Recommended** |

**Cost of the recommended shape versus the flat list: zero extra days.** Two group
headings instead of none. That is the whole difference. There is no budget argument for
the flat list.

**⚠ DECISION PM-1.** Surbhi can overrule this in one sentence — "I want one flat list" —
and the designer will design it. If she does, I ask that one line be written into the
brief: *the badge then counts rows, not work, and it will go quiet without the work being
done.* I would rather have it recorded than discovered.

### 8.2 What the badge counts — and the cost of excluding my own requests

**Recommended definition:**

> **Badge = unread notices + approvals waiting on me (excluding shift requests) +
> policies to acknowledge.**
> Summed **in the browser** from the two answers it just drew. Never a third query.

Three precision points, all **Confirmed in code today**:

1. **Not `get_inbox.total`.** It is `approvals + policies + my_requests`
   (`inbox_api.py:1132`).
2. **Not `approvals_total` either.** It *includes* `shift_requests`
   (`APPROVAL_PARTS`, `inbox_api.py:88`). The badge must sum `parts[]` and skip
   `shift_requests`, as Home already does (`portal.js:6594`). No screen exists where a
   manager decides a shift change, so counting it gives a number with no door.
3. **Excluding `my_requests` is a change to a shipped surface.** Home's chip counts them
   today (`portal.js:6655`). The rows also already appear in Home's pending list.

**⚠ DECISION PM-2 — the real trade-off, both options honestly:**

| Option | What it costs | What it buys |
|---|---|---|
| **A · Exclude `my_requests` from the badge *and* from Home's chip** (my recommendation) | One number on a live screen gets smaller for employees with an open request. One line in `hmPaintPending`, plus moving those rows under the "Waiting on someone else" heading on Home too, or they sit in a list that disagrees with the chip above them. Perhaps +0.25 day. | A number the person can clear by acting. One definition in both places. No employee ever stares at a "1" they cannot move. |
| **B · Keep `my_requests` counted everywhere** | An employee with a pending leave request carries a badge they cannot reduce — mildly Reverse (§4) | Zero change to a shipped surface. Zero risk of the two numbers drifting. |

**I recommend A**, because `inbox_api`'s own first rule is "a count must equal the list it
links to", and two different definitions of "waiting" in two places is the exact failure
slices 034, 042 and 076 were built to prevent. **But B is defensible and cheaper, and if
Surbhi does not want a shipped number to change this week, B is a fine answer** — in
which case the page simply counts the third group too and it is no longer "uncounted".

### 8.3 Three rules that travel with it into the spec, unsoftened

1. **Tapping a task navigates. It marks nothing. Ever.** A task has no read state, and
   giving it one is a new field for a behaviour nobody asked for.
2. **A task leaves the list only because the work was done, someone else did it, or it
   stopped being theirs.** No dismiss, no snooze, no X. A stale tap says which:
   "Already decided by someone else." / "The request was withdrawn." A scope change says
   nothing, because "you no longer approve for Rakesh" leaks an org change.
3. **Nothing about notices is cached in the browser.** 441 DTC logins share handsets.

**⚠ DECISION PM-3 (filters, carrying OPS-5 and ⚠ 1).** Filters work on the rows the feed
already returns — last 30 days, 100 rows — and the page says "Last 30 days". **My
recommendation: yes, browser-side.** Reaching beyond the window adds 1.5–2 days, new
pagination and a re-measured query budget (DevOps §5), for history we have never
promised. And **three chips, not four.** Low confidence on the fourth chip; it is one
line to change later and §10 of 01a tests it.

**⚠ DECISION PM-4 (the CXO badge, carrying ⚠ 2).** Count **kinds** for a CXO, matching
Home. A badge reading "214" on a five-minute phone check is noise, and Home already
treats them differently.

**⚠ DECISION PM-5 (badge colour, carrying ⚠ 3).** `--primary`, not red. Red is for
overdue or wrong; an unread count is ordinary. One CSS line.

**⚠ DECISION PM-6 (where the bell goes, carrying ⚠ 6).** Frappe's website navbar,
right end, immediately left of the avatar menu. The portal already rewrites that
navbar's brand and hides two of its items, so it is already our desktop top bar.
Engineer to confirm feasibility.

**⚠ DECISION PM-7 (the route shape, carrying OPS-4).** A hash route inside
`/hrms-employee`, **not** a new web page. A new address falls outside the nginx
compression whitelist and means editing the one file that serves production and dev.
I support DevOps' P1 here without reservation.

---

## 9 · Access expectations — who may see, change and share

**Written from HR norms and what each persona is hired to do, before the BA or the
engineer decide how.** This slice adds **no new field and no new kind of data.** It
changes **where** two existing feeds are shown, and it creates one new exposure: a
durable, addressable page holding 30 days of one person's HR messages, on handsets shared
by 441 DTC logins.

| Kind of data | Persona | May see | May change | May share | Purpose (their job) | Must NOT have | Class |
|---|---|---|---|---|---|---|---|
| **My own notices** (grooming marks, grooming reviews, announcements sent to me) | Employee / frontline | own rows only | mark own row read | no share, no export | know what the company told me | any colleague's notice row, by any route | **Kano-must** — a breach if wrong |
| | Line manager | own rows only | own rows | no | same as any employee | their team's notices. Being someone's manager is not a reason to read their grooming alert | **Kano-must** |
| | HR Manager | own rows only **in this surface** | own rows | no | this page is the person's own inbox, not an HR tool | other people's notice rows through this page | **Kano-must** |
| | CXO | own rows only | own rows | no | same | everyone's notices | **Kano-must** |
| | Announcement sender | **that they sent it.** Not who read it | — | no | confirm it went out | per-recipient read state (§10, ⚠ COMPLIANCE) | expectation, deliberately refused for now |
| **Approvals waiting on me** — colleague name, leave type, dates, claim amount and note, as already returned by `get_inbox` | Line manager | only rows where they are the named approver | approve / decline with a reason | no export, no share | decide their team's leave, expenses, goal updates, attendance fixes | **absence reason, health, passport, bank, pay** — none of it is in `ROW_KEYS` and none may be added | **Kano-must** |
| | HR Manager | rows in their company scope | correct and decide across their companies | no export from this page | fix and unblock across the company | other companies' rows | **Kano-must** |
| | CXO | **counts by kind**, not names | nothing from this page | no | one trustworthy number | 400 colleague names in a bell payload | expectation (and a privacy improvement) |
| | Employee (not an approver) | nothing | — | — | — | any approval row | **Kano-must** |
| **My own pending requests** (`my_requests`: my leave, my attendance fix, my shift change) | Employee | own rows, with the state sentence and the reason given to them | withdraw, where already allowed | no | "where has my request got to?" | a colleague's request | **Kano-must** |
| | Line manager / HR | only through the approval row they are deciding | as today | no | — | no new visibility from this slice | expectation |
| **Policies to acknowledge** | Everyone | the policies published to them | acknowledge | no | know the rules that bind them | nothing new | expectation |
| **The page itself, on a shared handset** | Frontline | only while signed in | — | — | — | **the previous holder's 30 days of messages, after sign-out or on Back** | **Kano-must** — new in this slice |
| **Who is an outside party here** (auditor, agency) | None | **no access at all** | — | — | this slice gives no outside party anything | this page is never shared, exported or printed | **Kano-must** |

**Conflicts between expectation and least privilege — questions for Surbhi:**

1. **An announcement sender expects to know whether their notice landed.** That is
   read-tracking of named colleagues. I am refusing it in this slice and naming security
   as the decider (§10). **If Surbhi wants it, it is its own slice with counsel.**
2. **A manager may reasonably expect "show me everything my team owes".** This slice does
   not give it and should not: the manager's bell counts *their own* work, not their
   team's inbox. Team oversight belongs on the Team page, where it already is.
3. **Nothing in this slice should make the badge smaller on purpose for a "cleaner"
   screen.** If any row is hidden, the number must drop with it.

### The five data-doors questions, answered in plain words

1. **Who can read this, and which Frappe door stops everyone else?**
   Only the person themselves. For notices, the door is Frappe's own permission condition
   on **Notification Log**, which pins `for_user` to the caller, plus `grooming._readable`
   per row. **Our page adds nothing — and it must not be where the limit lives.**
   Important: `notices.py`'s docstring says the Frappe condition exists; **neither the
   designer nor DevOps read Frappe's source today, and nor did I. It is an inference and
   it must be proved**, not assumed. For approvals, the door is `get_inbox`'s per-part
   scope (`permitted_companies`, `permitted_employees`, the named-approver filter).
2. **Was it tested as a plain staff login through the API, not only through the portal?**
   Not yet. It must be, and this slice is the moment: `/api/resource/Notification Log`,
   `frappe.desk.reportview.get` and `get_count`, `frappe.client.get_list` and
   `get_value`, link search, report view and CSV export, and share. **A test that passes
   because our page does not draw a field proves nothing.** This is OPS-10 and I adopt it.
3. **Does it work on a fresh site, and what does the real tenant look like?**
   Run the new tests on a **freshly created** site, not a copy (ALV-249 broke two tests
   that passed on a copy). Before release, a read-only count on DTC: how many
   Notification Log rows a plain staff login can list, and whether that number is their
   own rows only.
4. **How many bypasses were added, and where are they listed?**
   **My expectation is zero.** No `ignore_permissions`, no raw SQL, no new whitelisted
   endpoint, and **no client-supplied filter that names a doctype, a field or a user**
   (OPS-9, adopted). Filter chips are fixed names applied in the browser. If the engineer
   needs one bypass, it is a change of shape and comes back to this brief.
5. **What could a manager with a self-service role change or share?**
   Nothing new. They can approve or decline what they could already approve or decline,
   from one more screen. The slice grants no new write, no new field and no new export.
   The one thing to watch: a decision sheet reused on a new page must re-check permission
   server-side, not rely on the row having been drawn.

**And the new exposure, stated as two acceptance criteria rather than a design change:**

- **PM-AC-A:** nothing about notices or approvals is written to `localStorage` or
  `sessionStorage`. The portal keeps exactly one thing today (`sb-pinned`); this must not
  become the second.
- **PM-AC-B:** after `/logout`, pressing Back renders **nothing** from cache on the
  notifications route. Test it, as a real browser Back, on a shared-handset profile.

---

## 10 · Regulatory read

1. **Which regime?** India's **DPDP Act 2023** — personal data shown to the person it
   belongs to, plus colleague data shown to an approver who already sees it. No new
   category, no health, no passport, no bank, no pay. No AI. **No EU AI Act surface at
   all** in this slice. CERT-In: nothing new to log.
2. **Whose obligation?** The **employer's** (DTC). Our job is to make their duty easy to
   discharge: a limit that lives in Frappe's permission layer, no caching on shared
   devices, no export. This slice helps the customer, not just us.
3. **What does it make newly possible?** One thing only: **a durable, addressable page
   holding 30 days of one person's HR messages on a shared handset.** That is the
   compliance event in this slice, and §9 answers it with two criteria. Nothing new is
   collected. No decision is automated.
4. **The honest downside.** If this were on the front page: "HR portal adds a
   notifications page; the previous user of a shared phone could press Back and read it."
   We would not defend that. Hence PM-AC-B.

**⚠ COMPLIANCE — out of scope, named here so it is not lost.** *May an announcement
sender see who has read their notice?* `Notification Log.read` makes it trivial, which is
exactly why it needs a decision rather than an implementation. **Decider:
`hrms-security-privacy-engineer`, then Surbhi, with counsel.** It blocks nothing in this
slice. **I am not a lawyer.**

**Where a TODO blocked me:** product-context §5 has **no named compliance owner**
(`TODO — founder to name a person`). So I cannot name the human who signs off the
read-tracking question, or who would own a DPDP notice if PM-AC-B were ever breached.
I have had to write "Surbhi, with counsel". §8's four people-metric targets are also
`TODO`, which is why §12 below carries `baseline unknown — measure first` rather than
numbers inherited from strategy.

---

## 11 · Run-side reality

Nothing in DevOps §1 changes the size or the priority of this slice. In their words and
mine:

- No new container, volume, image, worker, scheduled job, dependency or alert. **₹0.**
- Parts 1 and 2 change **no server code**. Part 3 adds one call per non-Home page:
  **21 statements, 638 bytes, worst measured p95 215 ms against a 500 ms budget**
  (Measured by slice 044, Sept 2026, on fixture sites — not re-measured).
- Perspective I want kept: the portal page is already ~235 KB gzipped. This slice adds
  **638 bytes**. If a performance argument lands on this slice, it is not this slice's.
- **Three DevOps rows I adopt as product requirements, not engineering preferences:**
  **OPS-1** the bell takes `get_nav_counts` (numbers), never `get_inbox` (rows) — shipping
  colleague names into every page payload is Wave 1's worst security finding repeated;
  **OPS-4** hash route, no nginx change; **OPS-10** the door list on Notification Log.
- **OPS-3** — measure `get_nav_counts` on a DTC-shaped copy before part 3 ships. I adopt
  it. It is the one number this slice genuinely does not have.
- **No cache of the badge** (OPS-11). Agreed, and the product reason is the strongest one:
  a cached badge is wrong in the seconds right after the person acts, which destroys §6.

---

## 12 · Success criteria

Four measures. **Every baseline is unknown, and I will not invent one.** Instrumentation
must be cheap — a count, not a new analytics module.

| # | Measure | Kind | Baseline | Target | How it is instrumented |
|---|---|---|---|---|---|
| 1 | **Share of leave and expense approvals decided from the notifications page or its bell**, of all decided in the portal | leading, adoption | **0** — the surface does not exist (**Confirmed**) | ≥ 20% within 4 weeks of DTC go-live | The decision already records which screen raised it, or one route field on the existing call. Engineer to confirm the cheapest honest count. ⚠ if it needs a new field, drop this measure rather than add one. |
| 2 | **Median days an approval waits** at DTC, before vs after | lagging, efficiency | `baseline unknown — measure first`; `waiting_since` already exists, so it is computable from today's data retrospectively | down 25% at 6 weeks | A one-off report over `waiting_since` on decided rows. No new storage. |
| 3 | **Unread notices older than 14 days, per employee** at DTC | lagging, quality | `baseline unknown — measure first` | down 50% at 6 weeks | A read-only count over Notification Log. "Mark all as read" should move this. |
| 4 | **Does the badge equal its lists?** Zero defects reported where the number and the groups disagree | leading, quality | 0 reports (surface does not exist) | **0**, for ever | The disjoint-sets test (OPS-8) plus support tickets. A single confirmed mismatch is a kill criterion. |

**Banned here:** bell clicks, page views, logins. A bell that is clicked and teaches
nothing is worse than no bell.

**No AI in this slice**, so no acceptance, override or escalation rate.

---

## 13 · Thriving-workplace lens

| Lens | One line |
|---|---|
| **Engagement** | Yes — momentum and agency. A number that falls because you did the work is the smallest honest reward loop in the product, and today a laptop user gets no signal at all. |
| **Collaboration** | Yes, at the moment it matters. Rakesh's leave request becomes visible to his manager on whatever screen the manager is already on, instead of waiting for them to visit Home. |
| **Inclusiveness** | The risk is real and answerable: 441 DTC staff on **shared** handsets (so no push, no cache, no sound), Hindi at parity for ~5 new strings, 44 agency staff on Contract who see the same page, 12 px text floor and a 44 px target on a phone, 24 px on desktop, and three chips that wrap at 360 px and 200% text. A new joiner sees both groups empty, so the page must say what it is *for*. |
| **Transparency** | It makes visible only what the person is already entitled to see, in one more place. Nothing about anyone else becomes visible. The one thing we are refusing to make visible — who read an announcement — is refused precisely because it would surveil the least powerful person in the picture. |

---

## 14 · Risks and the honest downside — red-teamed

| # | What breaks | Severity | Cheapest way to find out before building |
|---|---|---|---|
| 1 | **The badge goes quiet without the work being done** (a flat merged list, or reading clearing tasks) | **Worst outcome in the slice** | Settle §8.1 at this gate. Then one line in the usability session: *"the badge was 7, you read the page, what should it be now?"* |
| 2 | **Two numbers disagree** — bell says 5, Home chip says 7 | High. It is the failure 076 exists to prevent | Settle ⚠ PM-2 at this gate. Then OPS-8's disjoint-sets test, plus one test asserting badge = sum of the drawn groups. |
| 3 | **Double counting** the day someone writes a Notification Log row for a leave approval | Medium. The sets are disjoint **today** (Fact) | OPS-8: assert the two doctype sets stay disjoint, in a test that fails if anyone adds one. |
| 4 | **10× the data.** An HR Manager or a long-serving employee with hundreds of unread notices | Medium | Count Notification Log rows per user at DTC **before** the design step. If the top user is in the hundreds, "Unread notices" stops being a filter and becomes the main view, and the page shape changes. This is the designer's biggest unverified assumption and mine. |
| 5 | **Bad or missing data** — a notice whose document was deleted, an approval row with no `waiting_since` | Low | `grooming._readable` already drops unreadable rows. The design must draw a row with no waiting line without saying "waiting undefined days". |
| 6 | **A manager changes mid-flow / an employee leaves** | Medium | The row simply vanishes on refresh, and a stale tap says "Already decided by someone else." Never a raw server error, never a silent no-op, and never "you no longer approve for Rakesh". |
| 7 | **One bad part takes the whole bell down** — ALV-250's failure, now on every page instead of only Home | Medium | OPS-6: keep both calls failing silently, badge unchanged, no toast. Test with one part raising. |
| 8 | **A shared handset leaks the previous holder's 30 days of messages** | High, and new in this slice | PM-AC-A and PM-AC-B. A manual Back-after-logout test on a real phone costs ten minutes. |
| 9 | **The limit turns out to live in our page, not Frappe's permission layer** | High — this is ALV-249's shape | OPS-10's door list, as a plain staff login, on a fresh site, **before** anyone claims this slice is safe. Nobody has read Frappe's own condition for Notification Log. |
| 10 | **A new web page instead of a hash route** → an uncompressed ~1 MB page, and an nginx file that restarts production | High, entirely avoidable | ⚠ PM-7, settled at this gate. |
| 11 | **Support tickets this would create** | — | "The bell says 5 but I see 4 rows." · "I read everything and the number is still 3." · "I cannot find a notice from last month." The answers are, in order: the disjoint-sets test, the group headings, and the words "Last 30 days" on the page. |
| 12 | **It gets built and nobody uses it** | Medium — this is one customer voice, no ticket, no lost deal | Measure 1 in §12. If it is near zero at 4 weeks, see Kill criteria. |

---

## 15 · Cost ladder

| Rung | Verdict |
|---|---|
| 1 · Already there | **Rejected.** Frappe's notification dropdown is a **Desk** UI; ESS staff have no Desk. The ESS portal is a website page whose navbar carries no bell. **Confirmed by the fact that slice 076 had to build `notices_feed` and its own bell.** Part 1 is *nearly* rung 1 — the markup and the call already exist on desktop and one CSS line hides them. |
| 2 · Configuration | **Rejected.** There is no setting that shows a bell on a laptop. |
| 3 · Customisation | **Rejected.** A Notification or a Workflow sends a message; it does not draw a screen. |
| **4 · New code — front end only** | **This is the whole slice.** One button placed in the existing desktop chrome, one panel in an existing JS file, one sidebar nav item, two keys added to an existing return, CSS. **Two endpoints that already exist, no third filter.** |
| 5 · New DocType | **Rejected, and it is load-bearing.** The only thing needing storage would be a per-task "seen" flag. §8.3 rule 1 says we never have one. No field, no DocType, no migration. |
| 6 · New app | No. |

**Why not a merged server endpoint, even though it would be tidier:** it is a third filter
expression over data two endpoints already answer, which is the thing `inbox_api`'s own
docstring forbids, and it buys one round trip nobody has measured as a problem. I hold the
designer's line.

---

## Subtract pass

I read this brief again asking only what I could delete. **Removed:**

- **A fourth success measure on "notices read within 24 hours"** — it would have needed a
  new timestamp read per row and it measures our screen, not anyone's day.
- **A "notification preferences" line** I had drafted under the employee persona (choose
  what appears in your bell). It is BambooHR's per-category switch wearing different
  words, which §3 already refuses, and it is a settings page by the back door.
- **A phased plan** — I had parts 1+2 as "slice A" and part 3 as "slice B". Phases are
  not a plan, and all three parts together are 2–3 days with one WOW. One slice.
- **A recommendation to fix the five stale sidebar badges** — moved to "worth doing
  later" with a reason, not carried as scope.
- **An "evidence of value" paragraph** restating the competitor table. One table is enough.

**Kept despite the pass, each with a reason:** the Access expectations table (mandatory,
and this slice has a genuinely new exposure); the §8.2 `my_requests` trade-off (it is the
only place the cost of the recommended shape is written down); and the four piles (they
are how Surbhi can cut this slice in one sentence).

---

## Open questions

Only the first two **must** be answered before the design step starts. The rest improve
the outcome and can be answered at the design gate.

| # | Decision | Owner | Blocks | My recommendation |
|---|---|---|---|---|
| ⚠ **PM-1** · **must know** | One place with **two visible groups**, or one **flat list**? | **Surbhi** | The page's whole shape, and whether the badge can be trusted | Two groups. Costs zero extra days. If you want a flat list, say so and we record that the badge will go quiet without the work being done. |
| ⚠ **PM-2** · **must know** | Does the badge exclude the person's **own pending requests** — and does Home's chip change to match? | **Surbhi** | The badge formula and one line on a live screen | **Option A: exclude, and change Home to match** (+~0.25 day). Option B — keep counting them everywhere — is cheaper and safe; it just leaves an employee a number they cannot clear. |
| ⚠ **PM-3** · should know (carries OPS-5, ⚠ 1) | Filters over the rows already fetched (last 30 days, 100), or must they reach further? And three chips or four? | **Surbhi** | ±1.5–2 days and the server query budget | Browser-side over the existing window, with "Last 30 days" on screen. Three chips. |
| ⚠ **PM-4** · should know (⚠ 2) | For a **CXO**, does the badge count rows or kinds? | **Surbhi** | The badge rule for one persona | Kinds, matching Home. |
| ⚠ **PM-5** · nice to know (⚠ 3) | Badge colour: red or `--primary`? | **Surbhi** | One CSS line | `--primary`. Red is for overdue or wrong. |
| ⚠ **PM-6** · should know (⚠ 6) | Bell in Frappe's navbar (top-right) or the sidebar footer? | `hrms-fullstack-engineer` on feasibility, then **Surbhi** | The bell's position | The navbar. Already our desktop top bar; top-right is where all six competitors put it. |
| ⚠ **PM-7** · must know, and I believe it is settled | Hash route inside `/hrms-employee`, not a new web page? | **Surbhi** | Whether `deploy/nginx.conf` — the file that serves production — is touched | Hash route. No nginx change. |
| ⚠ **PM-8** · should know (⚠ 5) | Do the five stale sidebar badges get fixed with the bell? | **Surbhi** | Scope only | **No — separate slice.** But note the bell will make them look wrong. |
| ⚠ **PM-9** · ⚠ COMPLIANCE, out of scope | May an announcement sender see **who read** their notice? | `hrms-security-privacy-engineer`, then **Surbhi** with counsel | Nothing here. It will be asked for. | Out of scope. Its own slice. |
| Evidence required | How many unread Notification Log rows does the heaviest DTC user carry? | `hrms-fullstack-engineer` or DevOps, read-only count | Risk 4, and whether "Unread notices" is a filter or the main view | Count it before the design step. Ten minutes. |
| Blocked by a `TODO` | Who is the **named compliance owner** (product-context §5)? | Founder | Who signs off PM-9, and who owns a notice if PM-AC-B ever fails | Name a person, not a function. |

---

## Assumptions

- `[ASSUMPTION]` In all six benchmarked products, notifications sit in the base tier and
  are never an add-on. I opened no pricing page. **Evidence required** before anyone
  repeats it to a customer.
- `[ASSUMPTION]` A typical DTC employee carries single-digit unread notices and
  single-digit tasks, so the page needs no pagination beyond the existing caps.
  **Unverified** — see Risk 4. This is the assumption most likely to change the page.
- `[ASSUMPTION]` Both existing calls answer inside the ≤ 500 ms p95 budget at DTC's ~600
  staff. The only measurements are slice 044's from September 2026, on fixture sites with
  no pay rule set enabled. OPS-3 should close this.
- `[ASSUMPTION]` Frappe's own permission condition for Notification Log pins `for_user` to
  the caller. **Nobody on this slice has read Frappe's source. It is an inference from a
  docstring and must be proved through the API, as a plain staff login, on a fresh site.**
- `[ASSUMPTION]` Reusing `hmLeaveSheet` / `hmExpenseSheet` on the new page is clean. If it
  is not, drop approve-from-the-page to "later" rather than writing a second sheet.
- `[ASSUMPTION]` Nothing in the slice touches the phone app, because mobile is a PWA over
  the same portal (Surbhi's decision, 24 Oct 2026). **No mobile artifacts, no mobile
  engineer.**
- `[ASSUMPTION]` DTC remains the only tenant where this matters in the first six weeks,
  so the baselines in §12 are DTC's.
- **Nothing in this brief was seen in a browser.** The designer could not run Docker, and
  I read code, not screens. Every code claim here I checked in the file myself and
  labelled **Confirmed**; everything else is labelled.

---

## Kill criteria — the observation that would make me stop

1. **The badge cannot be made to equal its lists.** If the two feeds turn out to overlap,
   or the number needs a third query to be right, stop part 3 and ship parts 1 and 2. That
   is a clean stopping point with zero server code changed (DevOps §5).
2. **The heaviest DTC user turns out to carry hundreds of unread notices.** Then the page
   is a different page and this brief is wrong. Re-scope before designing.
3. **Any part of this needs a new field, a new DocType or an `ignore_permissions`.** Stop
   and come back to this brief. The shape has changed.
4. **Measure 1 is near zero at four weeks after DTC go-live** — nobody decides anything
   from the new surface. Then the bell was furniture, and nothing further gets invested in
   it. Do not "improve" it; leave it.
5. **The door list (OPS-10) shows a plain staff login can list a colleague's notification
   rows.** Stop everything, tell Surbhi first, open a ticket, read-only counts only. That
   is ALV-249's shape and it outranks this slice entirely.

---

## Handoff note — to `hrms-ux-designer` (design step) and `hrms-business-analyst`

**Two things must be settled by Surbhi before the design step starts: PM-1 (two groups or
one flat list) and PM-2 (does the badge count the person's own pending requests, and does
Home's chip change to match).** Everything else in the design can proceed on my
recommendations.

**Designer:** I have accepted your §5 recommendation in full, as a product decision and
not a layout one, and I have carried your three unsoftenable rules into §8.3. Two
corrections you will want: `approvals_total` **includes** shift requests, so the badge
must sum `parts[]` and skip them; and excluding `my_requests` is **not free** — Home's
chip counts them today, so the Home surface changes too. Also carry NB3 (the 11 px badge,
fixed in `.notif-badge` only) and NP1 (the page needs a sidebar nav item) into the design
rather than discovering them in markup. And please count Notification Log rows per user at
DTC before you draw the page — Risk 4 is the one thing that could make your §6 wrong.

**Analyst:** PM-AC-A and PM-AC-B in §9 are acceptance criteria, as written. OPS-1, OPS-4,
OPS-6, OPS-8, OPS-9 and OPS-10 are adopted and must each map to an `AC`. The Access
expectations table in §9 is yours to turn into per-field, per-record rules with the Frappe
door named for each — and the most important row is the one where I say the limit must
**not** live in our page code.
