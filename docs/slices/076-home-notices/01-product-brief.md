# 076 · Home page: Pending, Notices (announcements + notifications), Birthdays and anniversaries, a balanced layout

*Updated 27 Oct 2026 (second pass): added sections 4a and 4b. Wherever the text below says "Notifications widget", read "Notices".*

Brief by the product manager · 27 Oct 2026 · YouTrack ALV-240 · Risk tier: **2 overall; the "who may message whom" rule is Tier 1** (it is branch and company scope, and personal data). Status: DRAFT for Surbhi's decision. I recommend; Surbhi decides.

**Bad news first.**
1. **Expense approvals do not exist in the portal for managers.** I found only the employee's own claims screen. Managers approve expenses in Desk. So "expense" in the manager's Pending list cannot be reused. It is a separate decision (D5).
2. **The Home page does not scale to the "balanced" request by deleting Activity alone.** Removing the card leaves the left column with only the goal sections, which are hidden for many people. Balance is a layout rule, written below, not a side effect.
3. **Frontline staff may have no login.** A notification needs a user. I could not check how many DTC staff have one (D3).

## 1 · The job, and who it is for

*"As an employee, when I open the portal I want to see what is waiting on me and what the office told me, without hunting through five screens."* And for HR: *"When something changes for the floor, I want to tell all of them, or only some, now or on Monday morning, without WhatsApp."*

Personas: **Employee** (main), **Manager**, **HR Manager** (the sender), **CXO**. Frontline wins any design trade-off (product-context section 2).

## 2 · Home today (read from code, Confirmed)

Home is `templates/includes/ess/parts/home.html`, painted by `loadHome()` in `portal.js`. A 2-column grid (`.home-body-grid`: 1fr + 300 px, `align-items:start`; one column under 860 px).

| Where | Cards, in order |
|---|---|
| Top | Check-in hero (all personas) |
| Left column | Day widget · **Activity** · My Goals (hidden if none) · Team Goals (managers only, hidden if none) |
| Right column (300 px) | Leave balance (hidden if none) · Pending Approvals (leave only, managers, hidden if none) · Holidays · My Documents · Policies |

By persona today:
- **Employee:** hero, day, activity, goals, leave, holidays, documents, policies. No "waiting on me" card at all, unless an item exists.
- **Manager:** adds Team Goals and a leave-only approvals banner.
- **HR Manager and CXO:** the same page as a manager. Nothing is HR- or CXO-specific on Home. (They get the bell badge, below.)
- **Phone:** one column, same order. Activity sits above goals, so the useful cards are pushed down.

**Why it looks unbalanced today (Confirmed from the code):** the right column is a fixed 300 px and the cards in each column are hidden when empty. So the column heights depend on who is looking. One person gets a tall left column and a short right one. Others get big gaps. Activity (the card to remove) is what fills the left column for most people.

**The Activity card:** `homeActivity()` and `renderActivityFeed()` call `hr_api.get_portal_activity` (7 days). Slice 070 already hides it when empty. It is a record of the employee's own clicks. That is activity logging, close to the "no passive monitoring" line in product-context section 6, so removing it is also safe. Remove the card, the two JS functions, the three call sites (lines ~5611, 6223, 8666) and the endpoint if nothing else calls it (engineer to grep).

## 3 · What already answers "what is waiting on me" — reuse first

I counted **eight** surfaces. Seven exist. One is missing.

| # | Surface | Covers | Live portal? |
|---|---|---|---|
| 1 | Home "Pending Approvals" banner (`get_employee_dashboard`) | leave, manager only | yes |
| 2 | Bell panel (`goals_api.get_pending_approvals`, count version for the badge) | goal and KPI updates | yes |
| 3 | Bell panel grooming section (`my_notices`) | grooming notices | yes |
| 4 | Progress approvals card, Team panel (`hr_api.get_pending_approvals`) | goal evidence | yes |
| 5 | Attendance-fix review queue (`acReviewQueue`) | attendance corrections | yes |
| 6 | Team panel leave approvals | leave | yes |
| 7 | **`inbox_api.get_inbox` / `get_nav_counts` (slice 034/042)** | **six parts in one call: leave approvals, goal updates, attendance fixes, shift requests, policies to read, my own open requests** | server side live; its screen is in the discarded redesign |
| 8 | Expense claim approvals | expenses | **not in the portal** |

**The finding that shapes the slice:** surface 7 already does what the Pending widget needs. It has one filter per part, a count that equals its list, scope declared per part, a 50-row cap, no `ignore_permissions`, and tests for guest, wrong persona and scale. Building a second pending query for Home would be exactly what its own docstring warns against ("the day somebody writes a second filter just for the badge...").

**Recommendation:** the Pending widget calls `get_inbox` and draws its parts. No new query. **Rung: new code on the front end only (a card), on an existing endpoint.** Rejected: a new pending DocType (nothing to store); the older per-surface calls (eight different filters).

### How the Pending widget differs by persona

All four see the same widget. What differs is what `get_inbox` returns for them (this is already how it works; I am not adding rules).

| Persona | Pending widget shows |
|---|---|
| *All four also see* | the same **Notices** card (announcements + notifications) and the same **Birthdays and anniversaries** card (own branch). Only senders also see a "Send a notice" link on Notices: HR Manager and Management only. |
| **Employee** | Policies to read · my open requests (leave, attendance fix, shift change) and their state. If a reporting-line approver is also on their record, they see approvals too. |
| **Manager** | The above, plus leave, goal and KPI updates, attendance corrections and shift requests from direct reports. Expenses: not unless D5 says yes. |
| **HR Manager** | Same parts, scoped to the companies and branches they look after (existing scope helper). Corrections follow the existing submit-permission rule. |
| **CXO** | Same parts, across companies they may see. Counts first, with a link in. No new CXO view. |

**Not shown, ever:** absence reasons, other people's decision notes, document ids in counts (these are already the `ROW_KEYS` rules). Two lines per row, not whole forms. Approve and decline stay on the existing screens, except the leave Approve/Reject buttons already on Home, which move into the widget rather than being rebuilt.

## 4 · Competitors, whole products

No live research was done in this run. Every cell is `[recall — verify]`.

| Area | Keka | greytHR | Zoho People | Darwinbox | BambooHR |
|---|---|---|---|---|---|
| Home | Mixed feed: check-in, to-do, birthdays, posts | Tiles for leave, attendance, payslip; inbox tile | Dashboard with activity, announcements, to-dos | Configurable widget Home, a "Things to do" list | Simple Home with "My requests" and a news feed |
| Pending actions | One "Inbox/To do" across leave, expense, attendance, more | Approvals inbox | Approvals inbox, all modules | One unified task list | Approvals list in the manager view |
| Announcements | Company posts with audience choice, comments | Announcements to all or groups | Announcements and a feed, with schedule | Announcements, groups and push | Company news |
| Schedule a send | Yes `[recall]` | Not sure | Yes `[recall]` | Yes `[recall]` | Not sure |
| Read tracking | Some | Rare | Rare | Some | Rare |

**All of them have:** social feeds, comments, likes, birthday and anniversary cards, email and push on every post.
**We deliberately do not do:** a feed, likes, comments, birthday walls, rich media, polls. For a shop-floor worker on a cheap phone, a notice is one short sentence and one tap to dismiss. Comments in a notice thread become an unmoderated HR problem for an HR team of one. We also do not copy per-person activity logging.
**Where we match:** one pending list, announcements to a chosen audience, a scheduled send.

## 4a · Announcements: who sends, who they may reach, and why not the bell

**Announcements widget vs Notifications card.** They are different things. A **notification** is the system telling *me* something about *my* work (a leave was approved, a goal update is waiting, a grooming mark). An **announcement** is a *person* in authority telling many people something. Both are stored as Notification Log rows (one table, one read flag, one bell count), but they are drawn in **one** widget on Home, not two.

**Recommendation: ONE widget, "Notices", not two.** Announcements first, pinned and marked "From HR" or "From <Name>, <role>"; system notifications below, in the same card, capped at 5 rows together. Reasons: the page must stay balanced (one card instead of two); the employee has one place to look; nothing is lost. The bell keeps its count. Rejected: two cards (more height to balance, and an employee cannot tell which to read first). If Surbhi wants two, the balance rule below covers it, at a cost of one more card.

**Who may send (Recommendation).** Two roles, no new role:
- **HR Manager** (existing role): may target everyone in the companies and branches they look after (existing scope helper, `permitted_companies` and `branch_scope`). One branch's HR cannot reach another branch.
- **Management:** the CXO / senior roles Surbhi names (D8). Default: users with the existing System Manager or a named "Announcer" role. May target the companies they may see. No new permission system.
- Line managers do **not** send in this slice (their team is small and they have the team screen). Employees never send.

**Who may target whom.** Audience = everyone in my scope, one company, one branch, or chosen people, always inside the sender's own scope. The form only offers what the sender may reach, and the server re-checks at send time. A sender can never reach outside their scope by editing the request.

**What an announcement carries:** a short message (300 characters), the sender's name and role, a send time. Nothing else.

## 4b · Birthdays and anniversaries

**What already exists (Confirmed).** Frappe HRMS ships daily birthday and work-anniversary **emails** (`hrms/controllers/employee_reminders.py`, switched in HR Settings: `send_birthday_reminders`, `send_work_anniversary_reminders`). It ships no portal widget. Employee already has `date_of_birth` and `date_of_joining`. The live portal has no such widget. The discarded redesign built only the person's *own* anniversary and left "joiners / other people" unbuilt on purpose (home_api D-8, a privacy decision), and `date_of_birth` is on the list of fields that must never leave the server in start-up calls. So the data is there; the widget and its privacy rules are the new part.

**Rung:** new code, one small endpoint on existing Employee fields. No new DocType. Rejected: copying the Frappe emails (email is muted at DTC; and an email goes out, a widget stays inside).

**What it shows:** this month's people, name and **day and month** only; for an anniversary add **years of service** ("Asha, 5 years"). Never the birth year, never age. A birthday row says "Birthday, 14 Nov".

**Who sees whom:** only people in the viewer's own company and branch (same scope rule as elsewhere). Presence is not a secret, but a name list across the company is more than a shop-floor worker needs.

**Excluded:** leavers (status not Active), people with no date recorded (not shown, not shown as blank), and **people who opted out**.

**Opt-out (DPDP):** a birthday is personal data and showing it to colleagues is a new use. Recommendation: **opt-out per person, one tick on their own profile, "Show my birthday and anniversary to colleagues"**, default **on for anniversaries, off until HR switches the feature on for the company**. A simpler alternative is a company-level switch only. ⚠ COMPLIANCE: whether a default-on display needs prior consent under DPDP is counsel's call (D10). I am not a lawyer. Until counsel says, ship **default off for birthdays** (the day is more sensitive), **default on for anniversaries**.

**Balance:** at most 5 rows are drawn, soonest first, with "See all (N)" which opens the full month. A long month never makes a tall card. If nothing this month: the short card says "No birthdays or anniversaries this month."

## 5 · Three ways to solve it; could we do nothing?

- **Conventional:** a feed with posts, comments and likes. Heavy, and wrong for this user.
- **Better (recommended):** one pending card on the existing inbox, one notifications card on the existing Notification Log, one small Announcement record that HR fills in.
- **Reimagined:** WhatsApp broadcast from HR. It would reach the floor best, but it needs a vendor, templates and consent. Not in this slice (a later decision).
- **Build nothing?** HR can already create Notification Log rows in Desk by hand, one at a time. That is not a send-to-all, not scoped to branch, not scheduled. So the new record is justified: **scheduling needs a stored record**, and scoping needs a place to enforce it.

**Rung:** the Announcement is a **new DocType (rung 5)**. Rejected below it: a Custom Field on Notification Log (it has no audience, no send time, no sender scope); a Frappe Notification rule (rule-based, set up in Desk, cannot be "send to these 12 people on Monday"). Everything else sits on rungs 1 and 4.

## 6 · Kano (proxy) and demand

- **Pending list: Must-be** `proxy`. All five competitors have one; its absence shows in an employee asking "where do I approve this".
- **Notifications from HR: Performance `proxy`.** Every competitor has announcements; buyers compare on audience control and scheduling.
- **Removing Activity: Indifferent.** Nobody asked for it, and Surbhi found it useless.
- Demand evidence: Surbhi's request, 27 Oct (seen). No customer survey. Evidence that would change this: whether DTC HR currently sends notices on WhatsApp and how often.

## 7 · The WOW

A shop-floor worker opens the portal Monday morning and sees, at the top: **"From HR: Tomorrow is a half day for the Noida unit. Tap to dismiss."** One short sentence from a person who knew it was for them. HR sees "Read by 212 of 240" on the record. That is the WOW: the right notice reached the right people, and HR knows it did.

## 8 · The thin slice

**Needed to validate now:**
1. Remove Activity.
2. Pending widget over `get_inbox` (rows capped, "N more" link to the existing screens).
3. One **Notices** widget over Notification Log: announcements pinned on top, system notifications below, 5 rows in all, unread count = the bell.
4. Announcement record: message (300 characters), audience, send now or at a chosen time, status. Senders: HR Manager and Management only.
5. Audience choices: **everyone in my scope**, **one company or branch in my scope**, **chosen people in my scope**.
5a. **Birthdays and anniversaries** widget: this month, name + day (+ years of service), own branch, 5 rows and "See all", leavers and opted-out people excluded, no birth year or age anywhere.
6. The scheduler job sends due announcements (it ticks every 3 to 4 minutes; "9:00" means "about 9:00").
7. HR sees sent counts and read counts. That is a count, not a list of who did not read (see risk 5).
8. The balance rule.

**Needed before it can ship:** sender scope enforced on the server (not just in the form); a test for each of branch, company, guest, a leaver, a double send; the DPDP look (section 10).

**Worth doing later:** email copy (D4), WhatsApp, repeat reminders, templates, push to the PWA, Hindi version of a notice, a "who has not read" list.
**Not doing:** a feed, comments, likes, attachments, polls, a rich-text editor, a new dashboard, a new workspace, a settings page.

### The balance rule (testable)

For a screen width of 1280 px and of 360 px, for each of Employee, Frontline employee, Manager, HR Manager, CXO, and for the empty case (nothing pending, no notices):

1. **Same height per row.** In the two-column layout, cards sitting side by side in one row differ in height by at most 1.5 times, or the shorter one stretches to match. No single card is more than 2 times the height of the median card on the page.
2. **No empty block.** No visible gap larger than 24 px (one card gap and a half) on the page between two cards or at the bottom of a column. The column ends within 120 px of each other on desktop.
3. **Widgets with nothing to show stay as short cards with a plain sentence**, not hidden. ("Nothing waiting on you." "No notices." "No birthdays or anniversaries this month.") They are not removed, so the page has the same shape for every person. (This reverses the slice 070 "hide empty cards" rule for these three widgets only. D6.)
4. **Lists are capped** (Pending: 5 rows; Notices: 5 rows; Birthdays and anniversaries: 5 rows) with a "See all" link. The three new widgets together add the same height for every persona, whatever the data. So a long list can never make a tall card.
5. **Phone:** one column, each card full width, same order for everyone: check-in, Pending, Notifications, then the rest. No card wider than the screen; no horizontal scroll.
6. Checked by a screen test at those two widths, five personas, three data sizes (none, few, 200 rows) that measures card heights and gaps.

The UX designer chooses how. The rule is the contract.

## 9 · Run-side reality

Not read: `07-devops-inputs.md` and `01a-ux-opportunities.md` do not exist yet in this slice folder, so I could not use them. **This brief is provisional until they arrive.** From the code: no new app, worker or storage. One new DocType. One more job on the existing scheduler. Home adds one call (`get_inbox`, the expensive one; it already has scale tests, so the DevOps budget check should rerun for Home) and one notifications call. Run cost: nil beyond that.

## 10 · Risks and the honest downside

| Risk | What I propose |
|---|---|
| **HR in one branch messages another branch.** | The sender's audience is fixed by the existing branch/company scope on the server. The audience list the form offers is the same list. A test sends as a Branch-A HR user and expects a refusal for Branch B. `Tier 1.` |
| **Spam or a mistake to everyone.** | A send to more than N people asks for one confirm ("Send to 240 people?"). Max length 300 characters. A limit of announcements per sender per day. The numbers N and the limit are D2. |
| **Personal data in a message.** | The form carries a plain warning. We do not read the text. It is HR's content. The notice is deleted with its retention period (counsel: not for ever). |
| **Scheduled send after someone leaves, moves branch or the sender leaves.** | The audience is resolved when it **sends**, not when it was saved. Leavers (status not Active) are skipped. The sender's right is checked again at send time; if it is gone, the send is held and HR is told. |
| **Double send** (the job runs twice, or two workers). | One record, one "sent" mark, set with a lock. Test it. |
| **People without a login** | See D3. |
| **Email muted at DTC until counsel/go-live.** | Email is not in this slice, so the mute is not touched. |
| **Read tracking becomes surveillance.** | HR sees "read by N of M". No per-person list in this slice. Read is the existing Notification Log read flag; no new tracking. |
| **10x data:** 1,000 employees, one send = 1,000 rows. | Fine in one batch. Over the 3 to 4 minute tick, chunk in the job. Measure first. |
| **The bell and the new Notifications card show different counts.** | Both read Notification Log. One number. |
| **Configured wrong:** nobody holds the HR role for the branch. | The Send button does not appear. |

**Regulatory read.** (1) DPDP: a new use of personal data (employee to user mapping, read flags). Not AI, not CERT-In. (2) The duty is the employer's; this helps them tell staff about policy and changes in an auditable way. (3) New: HR can message people; a read flag is kept. (4) We would defend it: the message is HR's and employees only see their own. ⚠ COMPLIANCE: whether a "read" mark is personal data needing a retention period; owner Surbhi with counsel. I am not a lawyer.

**Thriving lens.** Engagement: clarity ("what is waiting on me"). Collaboration: managers clear their queue sooner. Inclusiveness: one short sentence in plain words works for the frontline; Hindi is a later decision; those with no login are excluded (D3). Transparency: HR sees counts, not names; employees see only their own.

## 11 · Success measures

| Measure | Baseline | Target | Instrument |
|---|---|---|---|
| Time from request to manager decision (leave, correction) | baseline unknown, measure first | shorter than the 4-week average before | difference between created and decision date, no new tracking |
| Share of announcements read within 24 hours | none yet | about 70% at a branch (a guess; adjust after the first month) | read flag in Notification Log |
| HR notices sent through the portal rather than WhatsApp | unknown; ask DTC HR | most, in the first month | HR's own report; count of Announcements |
| Balance rule test passes at both widths, five personas | none | all pass | the screen test |

No logins or page views.

## 12 · Subtract pass

Removed from my first draft: a "company" audience tier separate from "branch"; a template library; repeat reminders; an email tick; a per-person read list; a new Home dashboard config. Removed on this update: a separate Announcements card (merged into Notices); line managers as senders; birthday emails (Frappe already has them); a birthday wall, wishes or comments. Added: one endpoint and one opt-out tick for birthdays. Still only one new DocType.

## Decisions Surbhi must make

| # | Question | My recommendation |
|---|---|---|
| D1 | Is the Pending widget built on the existing inbox (six parts), with approve/decline staying on existing screens? | **Yes.** Cheapest and already tested. |
| D2 | Limits on sending: confirm above how many people, and how many announcements per sender per day? | Confirm above 25; 5 a day. Change after the first month. |
| D3 | Do frontline staff without a login need to receive these? | Not in this slice. Tell me how many DTC staff have logins; if many do not, the answer needs another channel (SMS/WhatsApp, a separate slice). |
| D4 | Email copy of an announcement? | **No**, not now. Counsel/go-live still holds DTC email. |
| D5 | Manager expense approvals in Pending? | **Not in this slice.** There is no portal screen; building one is its own slice. Tell me whether DTC managers approve expenses at all. |
| D6 | Show "Nothing waiting on you" cards instead of hiding empty ones, for the balance? | **Yes**, for these two widgets only. |
| D7 | Is a hand-written notice in English only for now? | Yes. |
| D8 | Who counts as "management" who may send? | The CXO users you name, through a named role (an existing role, or one new role "Announcer"); each limited to the companies they see. Line managers do not send. |
| D9 | One Notices card (announcements + system notifications) or two cards? | **One.** Easier to balance, one place to look. |
| D10 | Birthdays and anniversaries: show to colleagues, with a per-person opt-out? Defaults? | Yes, branch-scope only, name + day + years of service, no age. Birthdays off until counsel confirms; anniversaries on. ⚠ counsel. |
| D11 | Should the three new cards stay hidden-when-empty (as slice 070) or show a short "nothing" card? | Short "nothing" card (same as D6). |

**Open questions** (owner, blocks): D3 count of DTC staff with a login (Surbhi; blocks reach claim). The 01a and 07 notes (UX designer and DevOps; block final sign-off). Whether the older Team-panel and bell surfaces are retired later (Surbhi; blocks nothing now).

**Assumptions:** `[ASSUMPTION]` employees map to a User where they have a login. `[ASSUMPTION]` the live portal is `portal.js`, since the redesign was discarded on 26 Oct. `[ASSUMPTION]` `get_portal_activity` has no other caller. `[ASSUMPTION]` "HR" means the existing HR Manager role scoped by company/branch.

**Kill criteria:** stop if DTC HR keeps using WhatsApp after one month and the read share is under 30%; if a branch-scope leak is found in testing and cannot be fixed with the existing helper; or if the balance rule cannot be met without hiding empty cards at the UX design check.
