# 076 · Home page design (UX), prototype v1

UX designer · 27 Oct 2026 · ALV-240 · Risk tier: 2 overall. Three parts are Tier 1: who may send and to whom, the expense decision (money), and birthdays (personal data). Status: DRAFT for Surbhi's review. I recommend; Surbhi decides.

Prototype: `docs/slices/076-home-notices/prototype-v1.html` (one file, sample data, open it in a browser). Not yet published as a link: I had no Artifact tool in this run, so the session that ran me must publish it.

Built on: `01-product-brief.md`, `01b-surbhi-decisions.md` (D1 to D11 and the later updates for D3, D8, D9, D10, D11). Where they differ, 01b wins.

**Bad news first.**
1. **The balance rule needed one trade-off.** When one card in a pair is empty and its neighbour is full, the empty card stretches to match (the rule's own escape clause). So "empty cards are short" is only true when both cards in the row are short. See Question Q1.
2. **I moved the Today strip into the check-in card.** Otherwise it pushes Pending down the phone page, and the brief fixes the phone order. See Question Q2.
3. **Leave Approve and Reject now sit in a sheet, one tap further than today.** That is what keeps every Pending row the same height. See Question Q3.
4. **Expense approval needs new server code that moves money.** It is Tier 1. See section 5.

## 1 · Frame

Who: every employee, opening the portal in the morning, on a laptop or a 360 px phone. What they want: what is waiting on me, what did the office tell me, who is celebrating. Senders (people given the Notice Sender access) also want to tell a group something in under a minute.

Personas drawn: Employee, Frontline employee, Manager, HR Manager, CXO. Frontline wins any trade-off (phone, 44 px targets, one sentence per notice).

Persona check:
| Persona | What changes |
|---|---|
| Employee | Gets Pending (policies, own requests), Notices, Birthdays. Cannot send. Can hide themselves from Birthdays. |
| HR Manager | Everything above plus approvals in their scope, and "Send a notice" if they hold the access. Controls the birthdays switch and sees who holds the access. |
| CXO | Pending shows counts by kind, not rows. "Send a notice" if they hold the access. |

One-way rule: no manager convenience costs an employee anything. The only thing a manager sees that others do not is approvals. Senders see read counts, never a list of who has not read.

## 2 · Evidence and rung

- **Fact** (read from code): Home is `parts/home.html` plus `loadHome()`. Grid is `.home-body-grid`, 1fr + 300 px, `align-items:start`. Cards hide when empty. That is why columns end at different heights.
- **Fact** (measured, prototype): see section 3.
- **Not captured:** I did not open the live local portal in a browser in this run. The existing cards (Leave balance, Holidays, Goals, Team goals, Documents, Policies) are stand-ins labelled "Existing card" in the prototype. Their real heights vary. The balance numbers below hold for my stand-ins and must be re-measured on the real cards at build (the screen test in brief section 8 point 6 does this).
- **Rung:** new front-end code and one new Role. Pending uses `get_inbox` plus one new part (expenses). No new DocType beyond the brief's Announcement. No new screen for who may send (section 6 option A).

## 3 · Layout grid

Rule behind every layout: **one two-column grid made of rows, not two independent columns.** Cards in a row stretch to the same height. Hidden cards drop out and the rest reflow, so there is never a hole. A lone last card spans the full width. This replaces the fixed 300 px right column.

Card order (same for everyone; phone is this order in one column):

| # | Card | Shown to |
|---|---|---|
| 1 | Check-in (with the Today strip inside it), full width | all |
| 2 | Pending for you | all |
| 3 | Notices | all |
| 4 | Leave balance (existing) | all |
| 5 | Birthdays and anniversaries this month | all, if the organisation switch is on |
| 6 | Upcoming holidays (existing) | all |
| 7 | My goals (existing) | if they have goals |
| 8 | Team goals (existing) | managers, if any |
| 9 | My documents (existing) | if any |
| 10 | Policies (existing) | if any |

Desktop 1280 px (sidebar 240, page padding 24, so the grid is 992 px wide, two columns of 488 px, gap 16): pairs fall out as Pending + Notices, Leave + Birthdays, Holidays + Goals, Team goals + Documents, Policies alone and full width. Switch the Birthdays card off and the pairs shift: Leave + Holidays, Goals + Team goals, Documents + Policies. Still no hole.

Phone 360 px: one column, card width 328, gap 16, same order. Check-in, Pending, Notices come first, as the brief requires.

By persona (what differs in the layout, all else equal):
| Persona | Difference |
|---|---|
| Employee | Pending has policies and own requests. No Team goals. |
| Frontline | No goals, no policies card in my sample. Pending usually short. Same shape. |
| Manager | Pending carries approvals. Team goals shown. |
| HR Manager | Pending carries approvals in scope. Notices has "Send a notice". No Team goals in my sample (shows the odd-number case). |
| CXO | Pending rows are counts by kind. "Send a notice" if they hold the access. |

### Measured result (the "balance check" readout in the prototype)

I ran every combination in headless Chrome: 5 personas, 3 data sizes (none, few, many), 2 widths, birthdays widget on and off: **60 combinations, 0 failures** on these tests:
- Largest gap between cards: 16 px (limit 24).
- Columns end together (rows end flush): 0 px apart (limit 120).
- No card taller than 2x the median: tallest 467 px on a phone, median 223 to 279 px. Closest call was 2.0x. Passes.
- Lists capped at 5 rows (Pending, Notices, Birthdays): always.
- Nothing wider than the screen: always. Phone order check-in, Pending, Notices: always.
- Same-row ratio on natural height: most pairs 1.0 to 1.4x. **A few pairs are over 1.5x** (for example Pending with 1 row next to Notices with 2: up to 2.2x). Those stretch to match, which the rule allows. The readout names each stretched pair and its natural ratio, so the stretch is visible, not hidden.

Caveat: the "median" test depends on the real existing cards, which I did not measure.

## 4 · The cards: content and states

Every list card: header (title, count chip in words), up to 5 rows, footer "See all N" only when there are more than 5. Rows are at least 56 px and the whole row is the tap target.

### 4.1 Pending for you (built on `get_inbox`, D1)
- Row: line 1 the person (or the policy / your request), line 2 kind, detail, and "waiting N days". Right: "Review" (opens the Decide sheet) or "Open" (goes to the existing screen for that kind).
- Order: oldest first across all kinds. **Needs one engineering change:** `ROW_KEYS` carries no created date, so one key must be added, deliberately (`inbox_api.py` says adding a key is a reviewed act). If that is refused, fall back to kind order, but then a manager with 8 leave requests never sees an expense on Home. I recommend the key.
- Kinds: leave, expense (new), goal update, attendance fix, shift change, policy to read, your request.
- CXO: one row per kind with the count ("Leave approvals, 14 waiting · across your companies"), most first. Tap opens that kind's screen. No people on Home for a CXO. This follows the brief ("counts first, with a link in").
- See all: a sheet with every row (at most 50 per kind, the existing cap).
- Empty: "Nothing waiting on you." plus "Requests that need you, and policies to read, appear here."
- Never shown: absence reasons, others' decision notes, document ids (existing `ROW_KEYS` rules).

### 4.2 Notices (D9: one card)
- Unread only, announcements first ("Pinned", with sender name and time), then system alerts. Up to 5. The chip says "N unread" and **equals the bell number**. Tapping a row opens the full text in a sheet and marks it read; it then leaves the card. Read items stay in See all for 30 days, marked "Read".
- Footer: "Send a notice" (left, only for people with the access) and "See all" (right).
- Rows show 2 lines, then "…". The sheet shows the whole message (up to 300 characters).
- Empty and up to date: "You are up to date." / "No new notices. Older ones are under See all." Empty and never had any: "No notices." / "Messages from HR and management, and alerts about your work, appear here."
- Bell: opens the same See all sheet. One list, one number.

### 4.3 Birthdays and anniversaries this month (D10)
- Row: initials circle, name, "Birthday" or "Work anniversary · 5 years", day and month on the right ("Today", "29 Oct"). Never age, never birth year. Today and coming days first, then earlier days this month marked "earlier this month". Own branch only. Leavers, people with no date, and people who opted out are left out.
- Title: "Birthdays and anniversaries this month".
- Empty: "No birthdays or anniversaries this month." / "People in your branch who share these dates appear here."
- **Organisation switch off:** the card is absent, and the grid reflows (section 3). It does not leave a gap. The page is balanced in both states (measured).
- **Per-person opt-out:** My profile has one tick, "Show my birthday and work anniversary to colleagues in my branch", on by default, with "They see your name, the day and month, and your years of service. Never your age or birth year. You can change this at any time." When the organisation switch is off, the tick is hidden and the page says "There is nothing to set here right now." (no greyed control).
- ⚠ COMPLIANCE: counsel agreed orally (D10). A written note is still wanted before go-live.

### 4.4 Check-in card
Unchanged, plus the Today strip (shift line and four quarters) inside it. The Activity card and its code go (brief section 2).

### 4.5 Existing cards
Leave balance, Holidays, Goals, Team goals, Documents, Policies keep their content. Only their position and width change. Goals, Team goals, Documents and Policies still hide when empty (slice 070). D6 and D11 apply to the three new cards only.

## 5 · Expenses: how a manager approves one from Pending (D5)

Two options. Recommendation: **B.**

| | A. Link to the existing Desk form | B. A Decide sheet in the portal (recommended) |
|---|---|---|
| What the manager does | Taps the row, lands in Desk, sets Approval Status, saves, submits. Three steps in a screen built for office staff. | Taps the row, sees employee, amount, type, date and note, taps Approve or Decline. |
| Phone | **Does not work.** The phone app is the portal as a PWA; Desk is never wrapped. A manager on the floor cannot approve. | Works. |
| New code | None | One new inbox part (`expense_approvals`, same scope helper, count equals list) and one new endpoint to decide. Reuses the same sheet as leave. No new DocType. |
| Risk tier | 2 | **1.** Approving books the claim to accounts (ALV-178). Needs the approver check, a double-tap guard, and a test for a non-approver. |
| Cost to build | about zero | small, but needs tests for permission and double decision |

Why B: the brief says act where you see it, and A fails on a phone. The sheet is shared with leave, so it is one new component, not two.

What the sheet says (money first, then the act):
- Title "Expense claim". Name. Amount in large type. Type and date. The note.
- "Waiting 8 days. Approving passes it to accounts for payment. You cannot take it back here."
- Buttons: "Approve" (main) and "Decline". Decline opens one required field, "Why are you declining? Pooja will read this." (140 characters), then the button becomes "Send decline". No reason, no decline.
- Result toast: "Approved. Pooja Mishra's claim of ₹2,300 goes to accounts." or "Declined. Pooja will see your reason."
- **Employee side** (small, needed so the decline is not a dead end): the employee's own claims screen must show "Declined: <reason>". `[ASSUMPTION]` the reason is saved in an existing field on the claim; the engineer picks which and confirms the employee screen can show it.
- **I could not check** whether Frappe's Expense Claim carries the approver on the claim in this tenant's setup, or which user may decide it. This is the engineer's first question.

Leave uses the same sheet: name, "Leave request", leave type, dates, days, "Approve" or "Decline" (with the same reason field). It calls the existing leave endpoints.

## 6 · Compose, and who may send (D8 simplified)

**Who may send:** whoever holds the **Notice Sender** access. This is one Role on their login, given by the organisation. Nothing is computed from levels or grades.
- **Where an admin gives or removes it: the existing Users screen, Roles list (tick or untick Notice Sender).** No new screen. Rung 2 (configuration): one Role record, shipped by a patch.
- **Alternative I rejected:** a small "Who can send" list in Organisation settings with Add and Remove. It is nicer for HR but is a new screen and a new endpoint (rung 4). I could not name something the Users screen cannot do.
- The prototype's Organisation settings page shows the people who hold the access as a **read-only list** and tells HR where to change it ("open the person under Users, then Roles, and tick or untick Notice Sender"). The list is a few lines of read-only code, so HR can check who has it. If Surbhi prefers no list at all, delete it.
- **Open for the analyst:** Should HR Manager hold Notice Sender by default? I assumed the patch gives it to existing HR Managers once at install and not again, so the organisation stays in control.
- "Send a notice" appears only for holders. A person without the access sees no button and no greyed button. The server re-checks at send time.
- Audience is limited to the sender's own company and branch scope. The form offers only what the sender may reach, and the server checks again.

**The Compose screen** (a full page, reached from "Send a notice" on Notices; "← Back to Home" returns):
1. **Message.** One box, "Message", with the counter "212 of 300". Hint under it: "Everyone you choose will read this. Do not put pay, health or other personal details in it."
2. **Send to** (radio): "Everyone I look after (412 people)" · "A branch or company" (then a list of only what they may reach, with counts) · "Chosen people" (a search box and ticks). A line under the section says live: "This reaches 240 people. Everyone has a login, so everyone sees it. People who have left are skipped."
3. **When** (radio): "Send now" · "Send later" (date and time; hint "It goes out at about this time, up to 4 minutes later", because the scheduler ticks every 3 to 4 minutes).
4. **Also send this by email.** Shown only when email is active for the tenant (D4). Not ticked by default. When email is not active the control is absent, not greyed. Review bar: "Email active for tenant".
5. **The one button says what happens:** "Send to 240 people", or "Schedule for 3 Nov, 9:00 am to 240 people". Under it: "You have sent 2 of 5 notices today."
6. **More than 25 people (D2):** a dialog, "Send to 240 people?" "You are about to send this now to 240 people. You cannot take a sent notice back." Buttons "Go back" and "Send to 240 people". 25 or fewer: sends at once.
7. **At 5 sent today:** the form is replaced by "You have sent 5 notices today." "That is the limit for one day. You can send again tomorrow."
8. **Errors, where they happen:** "Write a message first." / "Choose a branch or company." / "Tick at least one person." / "Choose a date and a time." / "Choose a time that has not passed yet." Focus moves to the field.
9. **After sending:** a green line "Sent to 238 people. They will see it on Home and in the bell." and the list "Notices I sent" shows each with "Reached 238 people · Read by 212 of 238" (a count, never names) or "Not sent yet" for scheduled ones.
10. **Cancel a scheduled notice:** a link, then a dialog "Cancel this notice? It is scheduled but not sent." This is **not in the brief**. I drew it because a scheduled mistake to 240 people with no way back is unsafe. Needs Surbhi's yes (Q4). Cost: one more status, "Cancelled".

## 7 · Organisation settings (smallest place)

The portal already has an Organisation settings page (`parts/org-settings.html`). I add one section there, visible to HR Managers:
- **Who can send notices:** read-only list and the "where to change it" line (section 6).
- **Birthdays and anniversaries on Home:** one switch. "On": "Staff see people in their own branch who have a birthday or work anniversary this month: name, day, and years of service. Never age. Each person can hide themselves in My profile." "Off": "Home does not show a birthdays and anniversaries card."
- Switching **off** asks first, because it changes Home for everyone: "Switch off birthdays and anniversaries? Home will stop showing this card for everyone in the organisation (412 people)." Buttons "Keep it on" and "Switch off". Switching on is one tap.
- A last-changed line ("Last changed by Kavita Rao, 20 Oct 2026") comes from the existing change history, not from a new record.

## 8 · Words (plain, short, translatable)

All strings are full sentences with numbers passed as values, so they can be translated whole. D7: notices are English only; the screen's own words can be translated later. Hindi runs about 30% longer. Rows clip with "…" and the whole text is one tap away, so a longer word cannot break the row. Dates are "29 Oct" (no year) in cards and "3 Nov, 9:00 am" with time, in the repo's format.

## 9 · Accessibility (WCAG 2.2 AA, nfr-budget §7)

- Every card is a section with a heading. Rows are real buttons (keyboard, Enter, Space). Focus ring is visible (3 px).
- Sheets and dialogs: `role=dialog`, `aria-modal`, focus moves in, Escape closes, focus returns to the row that opened it.
- Compose: every field has a label; errors are text with `aria-describedby`; reach line and counter are announced politely.
- Colour never alone: "Pinned", "Read", "Review", "Open", "waiting 8 days" are words. Count chips say "24 waiting", not just a number.
- Tap targets 44 px or more on a phone, rows 56 px. Field text 16 px. Nothing under 12 px (measured in the prototype).
- The bell badge sits beside the icon, not on it, and has an accessible name ("Notices, 20 unread").
- Switch has a name and state ("On"/"Off" in words).

## 10 · Privacy and refusals

- Birthdays: own branch, name, day, years of service only. No age, no year. Opt-out. Leavers excluded. No list of "who did not wish".
- Read counts: numbers only. No per-person read list.
- Pending: only the caller's rows (existing scope helper). The CXO sees counts.
- Compose: scope enforced on the server, not only in the form. A notice carries a plain warning about personal data.
- Nothing from the refusals list is drawn: no feed, no likes, no comments, no activity log (the Activity card is removed), no AI.

## 11 · Honest states and the network

- Each card loads on its own with a skeleton inside 300 ms (nfr-budget §2). One card failing shows "We could not load this. Try again" with a button, never a raw error or an endless "Loading…" (anti-pattern N4). Prototype shows only the loaded states (v1 limit).
- **Risk:** Home adds one expensive call (`get_inbox`) and one notices call. DevOps should rerun the budget check for Home.
- A send that times out may still have gone through. Compose must say "It may have gone through. Check Notices I sent before trying again" and check before re-sending (checklist item, 24 Oct). **Not drawn in v1.** Needs Surbhi's yes to add it to the parity table.

## 12 · Phone (words only)

Mobile is the portal as a PWA (no store, no Flutter shell, Desk never wrapped). Every screen here is a portal screen. Sheets become bottom sheets at the phone width. The decision and compose flows are portal pages, so they work in the PWA with no native part. Nothing here needs push; notices are read when the person opens Home. The expense option A fails exactly because Desk is not on the phone.

## 13 · Questions for Surbhi

| # | Question | Why it matters | My recommendation |
|---|---|---|---|
| Q1 | When one card in a pair is empty and the other is full, may the empty one stretch to match? | Otherwise the page is uneven, which you ruled out. | Yes (as drawn). The empty card carries a calm sentence. |
| Q2 | Today strip inside the check-in card? | It keeps the phone order check-in, Pending, Notices. | Yes (as drawn). |
| Q3 | Leave Approve and Decline in a sheet (one tap further than today)? | Keeps every row the same height. | Yes (as drawn). The sheet shows the context a manager needs. |
| Q4 | Cancel a scheduled notice? | Safety net, not in the brief. | Yes. |
| Q5 | Show full names in Birthdays, or first name and surname initial? | Personal data, same branch. | Full name (as drawn). |
| Q6 | Pending sorted oldest first needs one new key on inbox rows. OK? | A reviewed engineering change. | Yes. |
| Q7 | Decline must carry a reason (140 characters), shown to the employee? | Employees should understand a decline. | Yes. |
| Q8 | Notice Sender given by HR Managers by default at install? | Who holds the access on day one. | Yes, once, then the organisation owns it. |

## 14 · Parity table (everything drawn will be built exactly as drawn)

| # | Feature in prototype v1 | Built as drawn |
|---|---|---|
| 1 | Activity card removed | yes |
| 2 | Row-based two-column grid, equal columns, no 300 px column, reflow, lone last card full width | yes |
| 3 | Phone: one column, order check-in, Pending, Notices, then rest | yes |
| 4 | Check-in card with Today strip inside | yes (Q2) |
| 5 | Pending card: 5 rows, count chip, See all N, empty state | yes |
| 6 | Pending row text, "Review"/"Open", waiting days, oldest first | yes (Q6) |
| 7 | CXO Pending as counts by kind | yes |
| 8 | Decide sheet for leave (Approve, Decline with reason) | yes (Q3) |
| 9 | Decide sheet for expense (amount, type, date, note, Approve, Decline with reason) | yes (Q7) |
| 10 | Expense decline reason shown on the employee's claims screen | yes (small, not drawn) |
| 11 | See all sheet for Pending | yes |
| 12 | Notices card: pinned announcements first, alerts below, unread only, 5 rows, "N unread" equals bell | yes |
| 13 | Notice sheet (full text; opening marks read) | yes |
| 14 | Notices See all sheet, 30 days, "Read" marks | yes |
| 15 | Bell opens the same sheet | yes |
| 16 | Notices empty and up-to-date states | yes |
| 17 | "Send a notice" only for Notice Sender holders | yes |
| 18 | Birthdays card: 5 rows, soonest first, then earlier days, See all N, empty | yes |
| 19 | Birthdays absent when the organisation switch is off, grid reflows | yes |
| 20 | My profile opt-out tick, hidden when the switch is off | yes |
| 21 | Compose: message and counter, warning line | yes |
| 22 | Compose: audience (everyone / branch or company / chosen people) with live reach line | yes |
| 23 | Compose: send now or later with date and time and the 4-minute hint | yes |
| 24 | Compose: email tick, only when email is active, unticked | yes |
| 25 | Compose: button that names what happens, sent-today line | yes |
| 26 | Compose: confirm above 25 people | yes |
| 27 | Compose: limit of 5 a day screen | yes |
| 28 | Compose: inline errors with focus | yes |
| 29 | Compose: result line and "Notices I sent" with reached and read counts | yes |
| 30 | Compose: cancel a scheduled notice | only with Surbhi's yes (Q4) |
| 31 | Organisation settings: read-only list of Notice Sender holders and where to change it | yes |
| 32 | Organisation settings: birthdays switch, confirm on switch off | yes |
| 33 | Notice Sender role given in the existing Users screen | yes (no new screen) |
| 34 | "Existing card" tags, "Sample" banner, the review bar, the balance readout | **no** (review scaffolding only) |
| 35 | Existing cards (Leave, Holidays, Goals, Team goals, Documents, Policies) | content unchanged; only the grid changes |

## 15 · What the analyst must turn into acceptance criteria

1. Balance rule at 1280 and 360 px, five personas, none, few and 200 rows, birthdays on and off, with the readout numbers as the test. The median test must run on the real cards.
2. Pending: kinds, order, cap 5, See all, CXO counts, empty text; the new expense part; the one new inbox key.
3. Expense decision: approver check, no double decision, reason required for Decline, the employee sees the reason, a test for a non-approver and for a second tap.
4. Notices: unread only, pinned first, bell equals card, 30 days in See all, read on open.
5. Birthdays: scope, leavers, opted out, no age or year, switch off removes the card, opt-out hides the tick when the switch is off.
6. Compose: scope enforced on the server, 300 characters, confirm above 25, 5 a day, send later, email tick only when active, counts shown, cancel (if Q4 yes).
7. The Notice Sender Role: seeded once, given and removed in Users, checked at send time.
8. Accessibility items in section 9.

## 16 · Usability test plan (High impact: Pending and Compose)

Five people: one frontline employee on a 360 px phone, two managers, one HR person, one CXO. Tasks: approve one expense; find the notice HR sent today; send a notice to one branch for Monday 9:00. Success: each done unaided in under two minutes on a phone. Change the design if two people cannot find "Review" on an expense row or choose the wrong audience.

## 17 · Subtract pass

Removed from my own drawing: a separate Today card (folded into check-in); inline leave buttons (one sheet for both); a "Got it" button on notices (opening reads); a Pinned chip (one word and an icon); a per-person read list; a "who can send" editor (use Users); a language switcher; a dark-mode special; a filter on any list.
Not removed, and why: the 5-per-day limit screen and the confirm above 25 (Surbhi's D2).

## 18 · Not in this slice (for Surbhi to decide)

An employee's own pending expense claim in Pending (the claims screen already shows it); WhatsApp or push; templates; repeat reminders; a "who has not read" list; "may have gone through" wording on send timeouts (section 11); Hindi notices.
