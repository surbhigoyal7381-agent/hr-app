---
slice: 076-home-notices
artifact: 03-functional-spec
author: hrms-business-analyst
date: 2026-10-27
status: draft
inputs: [01-product-brief.md, 01b-surbhi-decisions.md, 01c-security-privacy-requirements.md, 02-design.md, 07-devops-inputs.md, prototype-v1.html]
---

# 076 · Home page: Pending, Notices, Birthdays, balanced layout. Functional spec

ALV-240 · Business analyst · 27 Oct 2026 · I specify; Surbhi decides.
File name: the handoff contract calls the spec `02-functional-spec`. In this slice `02` is already the design, so this is `03-functional-spec.md`.

**Risk tier.** Overall 2. Tier 1 stories (strong-model build, independent review, separate security check): messaging scope, the send job, the expense decision, birthdays. They are marked per story in section 9.

**How I read the prototype.** I read `02-design.md` in full (its section 14 is the parity contract) and used the wording it quotes. I did not re-read the 62 KB `prototype-v1.html` line by line. Where this spec quotes screen text, the engineer must copy the exact string from the prototype file, and the prototype wins on wording.

---

## Bad news first

1. **The leave Decline sheet needs a small server change that nobody listed.** The design (parity row 8) says Decline carries a reason. The existing `hr_api.action_leave(leave_id, action)` takes no reason, and Frappe's Leave Application has no decline-reason field (read in code). The 01c "subtract pass" said the leave sheet adds no server code. That is no longer true. See US-12 and open decision 3.
2. **The bell number changes.** Today the bell badge counts goal and KPI approvals plus grooming notices (`loadNotifBadge`, `gmPaintBadge`, read in `portal.js`). Parity rows 12 and 15 say the Notices chip equals the bell, with one list and one number. So after this slice the bell counts unread Notices only. Goal and KPI approvals move to the Pending card. This is a behaviour change for managers. Open decision 2.
3. **Sending to more than 200 people cannot happen inside the tap.** OPS-7 says write in chunks of 200 on the `long` queue. So "Send now" to 201 or more people is handed to a background job, and the page says "Sending…" instead of "Sent". That wording is not in the prototype. Open decision 1.
4. **A CXO who is a System Manager reaches every company**, not "only the companies they look after". The existing scope helper gives System Manager everyone (`access.py:276-278`, read in code). Q3=B holds only for a director who is not a System Manager. Open decision 6.
5. **The employee claims screen uses the claim's `remark` field as the claim's title** (`portal.js:7455`, `c.remark || c.name`). The decline reason cannot be written there. It needs its own field (US-17).
6. **Birthdays switch ships OFF** (Q2 working default). On day one of release the widget does not appear anywhere until HR turns it on.
7. **Permission tests do not run in CI** (01c section 9). They are proved on the local bench only.

---

## 1 · Cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Main** | New DocType `Announcement`; new endpoints; `inbox_api.py` (new part, new key); `hr_api.py` (filing sets approver; `action_leave` optional reason; Activity removed); `portal.js`, `home.html`, `org-settings.html`; hooks; patches |
| `hrms` (Frappe HR) | Yes, in place | `hrms/hrms/alvoraa_hr_core/access.py` gets one new scope function and is otherwise unchanged. Expense Claim, Leave Application, Employee, HR Settings are used as shipped |
| `frappe` | Used | Notification Log, Role, User Permission, Version, Email Account |
| `erpnext` | Used | Expense Claim posts to the ledger (GL Entry) on submit |
| `alvoraa_goals` | Read only | Goal and KPI updates already arrive through `inbox_api`. No change |
| `alvox_compensation` | No | Not in this bench |

HRMS domains touched: **leaves** (decision sheet), **expenses/payroll accounts** (approval books to the ledger), **org structure** (branch and company scope, employee fields), **goals** (rows in Pending only), **attendance** (Pending rows, check-in card holds the Today strip). Not touched: payroll runs, appraisals, learning.

Personas: Employee, Frontline employee, Manager (line manager and named expense approver), HR Manager (also a sender), CXO (also a sender if given the role), Notice Sender holder (a role, not a person type).

## 2 · Questioning the ask

The brief's stated problem is "what is waiting on me, what did the office tell me, who is celebrating, and HR cannot reach the floor without WhatsApp". Cause check: Surbhi observed it (27 Oct); the Home page hides cards when empty, so columns are uneven; Activity is useless. Nothing in the brief traces the problem to a wrong cause, so I proceed. Two "what happens after" checks:

- **Pending card:** the decision is "approve or decline now". The system already acts: the Decide sheet lets the manager finish from Home. Good.
- **Read counts:** "Read by 212 of 238" drives one decision, "do I need to send it again or tell people another way". HR cannot act on names (none shown). It is a count only. Accepted by the brief.
- **Birthdays:** drives no decision. It is a courtesy card. It stays because Surbhi approved it (D10) and it is off until she switches it on.

## 3 · Gap analysis (read from code, not recalled)

| # | Requirement | What exists today (quoted from source) | Verdict | Cost |
|---|---|---|---|---|
| G1 | Remove Activity | `hr_api.get_portal_activity` (`hr_api.py:1120`). Callers: `portal.js` lines 5617, 6223, 8666 plus `homeActivity`, `renderActivityFeed`. It uses `ignore_permissions` three times | **Drop** (delete card, two JS functions, three call sites, endpoint). Engineer re-greps before deleting | S |
| G2 | Pending card | `inbox_api.get_inbox` / `get_nav_counts` (six parts, scope string per part, `ROW_KEYS`, 50-row cap, `no_rows()`) | **Configure/Extend**: front-end card on the existing endpoint; one new key `waiting_since`; one new part `expense_approvals` | M |
| G3 | Manager approves expenses | Portal has only the employee's own list (`get_expense_claims`, `apply_expense_claim`). HRMS approves in Desk. Standard Expense Claim already has `expense_approver`, `approval_status` (Draft/Approved/Rejected/Cancelled), submit needs one of those (`expense_claim.py:199-201`), HRMS shares the claim with the approver on update (`share_doc_with_approver`, `hrms/hr/utils.py:800`) | **Extend**: one decide endpoint using the doc API; filing sets approver; one hook | M |
| G4 | No self-approval of expenses | HRMS check is off unless HR Settings `prevent_self_expense_approval`; Leave Application, Attendance Request, Grooming Mark already carry `refuse_own_submit` (`hooks.py:141,295,358`). Expense Claim does not | **Extend**: add the same hook to Expense Claim `before_submit` | S |
| G5 | Decline reason (expense) | Expense Claim has `remark` (used as the claim title on the portal). No decline field | **Customisation**: one Custom Field `alvoraa_decline_reason` on Expense Claim | S |
| G6 | Decline reason (leave) | `action_leave(leave_id, action)` has no reason. Leave Application has no such field. Frappe's Comment (standard) can hold text on any document | **Extend**: optional `reason` argument stored with `doc.add_comment`. No new field | S |
| G7 | Announcements to a chosen audience, now or later, with cancel | Nothing. Notification Log rows can be made by hand one at a time; Frappe Notification rules are rule-based. Brief section 5 rejected both | **Build new**: one DocType `Announcement` (rung 5). Cheaper rungs rejected: a Custom Field on Notification Log has no audience, send time or scope; a Notification rule cannot say "these 12 people on Monday" | M |
| G8 | Recipient rows | Frappe `Notification Log` (fields `subject`, `email_content`, `type`, `document_type`, `document_name`, `from_user`, `for_user`, `link`, `read`). `after_insert` emails unless type is in `notification_skip_email_types` = `["Alert"]` (01c bad news 2) | **Already there**: one Notification Log row per person, type `Alert`, `document_type = "Announcement"`. **No child table** for recipients. Read counts are COUNTs on these rows | S |
| G9 | Who may send | Roles exist; HR Manager exists. No "may send notices" role | **Configure**: one new Role `Notice Sender` seeded by a patch; given and removed in the existing Users screen (design section 6) | S |
| G10 | Sender scope | `access.permitted_employee_filters(user)`, `permitted_companies`, `permitted_branches`, `employee_in_scope` (all read). Non-HR, non-System-Manager users get `NO_EMPLOYEES` | **Extend**: one new function `notice_audience_filters(user)` next to them (Q3=B). Changing the shared helper would widen every other screen. Rejected | M |
| G11 | Scheduled send | Scheduler `all` event exists (`hooks.py:408`, `update_delivery_tracking` is the precedent); `long` queue exists | **Extend**: one job in `scheduler_events["all"]` that enqueues; no new queue or worker | M |
| G12 | Notices card and bell | Bell: `goals_api.get_pending_approvals(_count)` + `grooming.my_notices` (reads Notification Log for `Grooming Mark` and `Grooming Review`, with a readability gate) | **Extend**: one function lists unread Notification Log rows for the caller: announcements, plus the grooming notices through the existing `my_notices` gate. Card, bell and See all call it | M |
| G13 | Birthdays and anniversaries | Frappe HR sends emails only (`employee_reminders.py`); no widget. `date_of_birth`, `date_of_joining` are field-rights level 2 (`employee_field_rights.py:44`) so a plain employee cannot read them | **Extend**: one endpoint on existing Employee fields; no new DocType | M |
| G14 | Org switch for birthdays | Org switches use `ALLOWED_ORG_SETTINGS` + `set_org_setting` (`hr_api.py:3200,3272`), stored as a Default value with **no history**. HR Settings has `track_changes: 1` (`hr_settings.json:422`) | **Customisation**: Custom Field on HR Settings. The cheaper "Default value" rung was rejected because PRIV-6 and design section 7 need "last changed by" from Frappe's own history | S |
| G15 | Per-person opt-out | Nothing | **Customisation**: Custom Field on Employee, set only through the person's own endpoint | S |
| G16 | Balanced Home | `.home-body-grid`: 1fr + 300 px, cards hidden when empty (brief section 2) | **Extend**: front-end grid change, no server code | M |
| G17 | Email copy | No "email is active" helper exists in `alvoraa_portal/*.py` (searched) | **Extend**: one small helper, used by Compose and the job | S |

Single source of truth: the notice **record** is `Announcement`. The notice a person **sees** is their Notification Log row. The Announcement owns audience, time and status; the log row owns "read".

## 4 · Process flow

### A · Sending a notice

1. A Notice Sender taps "Send a notice" on Notices. The server checks the role (AC-14). No role: no button, and the endpoints refuse anyway.
2. Compose loads only the choices inside the sender's scope (AC-45). If scope is empty the page says "No one is in your scope. Ask HR." (AC-12).
3. Sender writes up to 300 characters, picks an audience, picks Now or Later, optionally ticks email (only if email is active).
4. Live reach line asks the server for a count (AC-45).
5. Sender taps the one button. **Decision:** more than 25 people? Yes: confirm dialog (AC-47). No: go on.
6. Server re-checks everything (role, scope, text, limits, time, the 5-a-day count, a same-text repeat within 2 minutes) and writes one `Announcement`.
   - **Unhappy:** any check fails: nothing is written, the page shows the exact error at the field (AC-49).
   - **Unhappy:** a repeat of the same text within 2 minutes returns the first notice (AC-18).
7. **Decision:** Now and 200 people or fewer: the server writes the rows in the request, status Sent (AC-30). Now and more than 200, or Later: status Scheduled, send time set. (Now over 200 is queued at once.)
8. Every tick (3 to 4 minutes on production, 60 s on dev) the job picks due notices, at most two, and enqueues a worker on `long` (AC-31).
9. The worker locks the notice, re-checks the sender (AC-27), resolves the audience **as the sender** (AC-23), writes Notification Log rows in chunks of 200, commits after each chunk, sets Sent (AC-25).
   - **Unhappy:** sender lost the role, was disabled, left, or has no scope: nothing sent, status **Not sent** with the reason; nobody alerted (Q6 default; AC-27, AC-35).
   - **Unhappy:** worker stops half way: status stays Sending; a later tick after 10 minutes resumes and skips people who already have a row (AC-32). Three stalled resumes: **Failed**, one Error Log row (AC-33).
   - **Unhappy:** scheduler is down: notices go late, not lost (AC-34).
   - **Unhappy:** the sender cancels a Scheduled notice first: the job finds Cancelled and sends nothing (AC-36, AC-38).
10. Recipients see it on Home Notices and the bell (flow B). The sender sees "Reached 238 · Read by 212 of 238" under "Notices I sent" (AC-39).

### B · Reading a notice
Home loads Notices (one call, own rows only). Tap a row → sheet shows the whole text → opening marks it read (Frappe `mark_as_read`) → it leaves the card, stays in See all for 30 days as "Read". The chip and the bell show the same number (AC-58).

### C · An expense claim, filing to ledger
1. Employee files in the portal. The server sets `expense_approver` (Employee's, else the Department's first expense approver) (AC-77). If neither exists the claim is still filed and sits with no approver (AC-78, open decision 4).
2. Approver opens Home. The Pending card shows the claim, oldest first among all kinds (AC-67, AC-80).
3. Tap "Review" → Decide sheet: name, amount, type, date, note, "Waiting 8 days…" (AC-90).
4. **Approve:** server locks the claim, checks the caller is the named approver with an Active Employee record and is not the claimant, sets Approved, submits through the doc API. Ledger entries are made by HRMS. Toast: "Approved. Pooja Mishra's claim of ₹2,300 goes to accounts."
5. **Decline:** the sheet asks "Why are you declining? Pooja will read this." (1 to 140 characters, required). Server stores it in `alvoraa_decline_reason`, sets Rejected, submits. No ledger entry.
6. **Unhappy:** not the approver, the claimant themself, an approver who has left, a second tap, two people at once: refused or "already decided", no second ledger entry (AC-84 to AC-88, AC-91).
7. The employee's claims screen shows "Declined: <reason>" (AC-92).

### D · Birthdays
Home asks the server. Switch off: empty list, no Employee query. Switch on: one query for people in the viewer's own company and branch, Active, with a date this month, not opted out. Returns name, kind, day, month, years. Five rows, soonest first, then "earlier this month". The person can hide themselves in My profile.

## 5 · Data model

**Rung check for every new thing.** One new DocType, three Custom Fields, one Role, one Employee-side tick. Nothing else.

### 5.1 New DocType `Announcement` (tenant side)

Module: Alvoraa Portal. Naming: series `ANN-.YYYY.-.#####`. Track Changes on. Not submittable. **It must be added to the tenant-side list that the billing/control-plane test reads**, or that test fails (slice 063 hit this: commit 4fdf8046). The name "Announcement" does not clash with any DocType in `hrms`, `alvoraa_portal` or `alvoraa_goals` (searched file names); engineer confirms against `frappe` and `erpnext` on the bench.

| fieldname | label | type | reqd | default | options / depends_on | Why an existing field cannot carry it |
|---|---|---|---|---|---|---|
| `message` | Message | Small Text | yes | | length 300 enforced in controller after trim | Nothing stores a notice's own text with its audience |
| `audience_kind` | Send to | Select | yes | | `Everyone in my scope` / `Company` / `Branch` / `Chosen people` | Audience is the thing Notification Log lacks |
| `audience_company` | Company | Link Company | | | depends_on kind = Company | same |
| `audience_branch` | Branch | Link Branch | | | depends_on kind = Branch | same |
| `audience_people` | Chosen people | Long Text | | | depends_on kind = Chosen people; JSON list of Employee ids; read-only | Ids are read only by the job for this one notice, never joined or queried. A child table would be a second new DocType for no gain |
| `sender_label` | From | Data | | | read-only; set at create as "<Full name>, <designation>" or just "<Full name>" | Frozen so a later role change does not rewrite what was sent |
| `send_at` | Send at | Datetime | yes | now for "Now" | | The job needs a due time |
| `status` | Status | Select | yes | `Scheduled` | `Scheduled` / `Sending` / `Sent` / `Cancelled` / `Not sent` / `Failed` | The job and the sender's list read it |
| `status_reason` | Reason | Small Text | | | read-only; plain words | PRIV-3: why it was not sent or failed |
| `email_requested` | Also by email | Check | | 0 | | SEC-17 |
| `email_note` | Email result | Data | | | read-only; e.g. "email not sent: email is off" | PRIV-3 / SEC-17 |
| `reached` | Reached | Int | | 0 | read-only; **also the resume cursor** | "Reached N"; the job resumes by skipping people who already have a row |
| `stalled` | Stalled resumes | Int | | 0 | read-only | The 3-strikes rule (OPS-9) |
| `sent_at` | Sent at | Datetime | | | read-only | PRIV-3 |

Not added, on purpose: a sender field (the record's `owner` is the sender); cancelled-by and cancelled-at (Track Changes writes a Version row with who and when, which PRIV-3's test asserts); a recipient child table; a read counter (counted from Notification Log, OPS-5); an idempotency token (the same-text rule does it).

**Permissions (DocPerm):** Notice Sender: create, read and write **if owner** (write allowed only while `status = Scheduled`, enforced in the controller). System Manager: full including delete. Nobody else has any row. All sends and cancels go through the endpoints in 5.5.

**Recipient rows.** Notification Log: `type = "Alert"`, `document_type = "Announcement"`, `document_name = <notice>`, `from_user = owner`, `for_user = recipient`, `subject = HTML-escaped message`, `email_content = same`, `read = 0`. No unique key is added to a framework table (upgrade-safe). Replay safety comes from "skip anyone who already has a row for this notice" in each chunk (this adapts OPS-8's unique key; same result, nothing added to a Frappe table).

### 5.2 Custom Fields

| On | fieldname | type | default | Note |
|---|---|---|---|---|
| HR Settings | `alvoraa_birthdays_on_home` | Check | **0** (explicit) | Org switch. Changes show in HR Settings Version history |
| Employee | `alvoraa_hide_birthday` | Check | 0 | Opt-out. Read-only in Desk. Set only by the person's own endpoint. Stored as "hide" so that default 0 = shown |
| Expense Claim | `alvoraa_decline_reason` | Small Text | | Read-only. Written by the decide endpoint |

Created in an `after_migrate` function with `create_custom_fields`, the same way `payroll_fields.py` and `org_job_link.py` do. The engineer checks how `employee_field_rights.py` should classify the Employee field (HR reads it, a plain employee reads only their own). `[UNVERIFIED — engineer to confirm]`.

### 5.3 Role
`Notice Sender`: `desk_access = 0`, in no Role Profile, no default role.

### 5.4 Changes to `inbox_api.py`
- `PARTS`: add `("expense_approvals", <route>)` after `leave_approvals`. `APPROVAL_PARTS` adds it. `parts()` builds it. The route for the "Open" link is the engineer's pick `[UNVERIFIED]`.
- `ROW_KEYS`: add `waiting_since` (a date string) to **every** part. New part's keys: `name, employee_name, expense_type, expense_date, amount, note, waiting_since, action`. Nothing else.
- Existing tests that assert "six parts" are changed on purpose, not relaxed.
- `waiting_since` source per part: the document's `creation` date for leave, attendance, shift, expense and my requests (`creation` is already read in `_part_my_requests`); `logged_on` for goal updates (already a key). For policies, the assignment date `[UNVERIFIED — engineer to name the field]`; a row with no date sorts last.

### 5.5 Endpoints (indicative names; module `alvoraa_portal/announcements.py` unless noted)
All refuse Guest (`_refuse_guest` pattern) and run no `ignore_permissions` except where stated.

| Endpoint | Who | Does |
|---|---|---|
| `notice_reach(kind, company, branch)` | Notice Sender | Returns the choices the sender may reach with counts, and the live reach number. No names |
| `notice_search_people(q)` | Notice Sender | In-scope Active people with a login: name and id, at most 20 |
| `create_notice(...)` | Notice Sender | Validates and writes the Announcement; may send at once |
| `cancel_notice(name)` | owner | Scheduled to Cancelled |
| `my_sent_notices()` | Notice Sender | Own notices with counts |
| `notices_feed(see_all)` | any user | The caller's own unread (or 30 days) rows, one function for card, bell, See all |
| `notice_mark_read(name)` | any user | Frappe `mark_as_read` on own row |
| `send_due_announcements()` | scheduler | Picks and enqueues |
| `hr_api` filing | employee | `apply_expense_claim` also sets approver |
| `decide_expense(name, action, reason)` | approver | Section 4C |
| `birthdays_this_month()` | any user | Section 4D. One counted `ignore_permissions` read (field rights level 2) |
| `set_birthday_hide(value)` | any user | Own Employee only; no employee argument |
| `set_birthdays_switch(value)` | HR Manager / System Manager | Writes HR Settings via the doc API |
| `notice_sender_holders()` | HR Manager | Names only |

Unavoidable `ignore_permissions` (counted against the CI number): writing another person's Notification Log row (one function), the birthdays read (one query). Removing Activity takes away three.

## 6 · States and transitions (`Announcement.status`)

| State | Set by | Next | Read-only | Notified |
|---|---|---|---|---|
| (before save) | | | | A draft is never stored. The page holds the text until the tap. **I cut "Draft": nothing could read it.** |
| Scheduled | create (Later, or Now over 200) | Sending, Cancelled, Not sent | audience, text, time (changing means cancel and resend) | none |
| Sending | the job, first act, under a row lock | Sent, Failed, Not sent | everything | none |
| Sent | job when every chunk is done | none (terminal) | everything | recipients get their rows |
| Cancelled | owner, only from Scheduled | none (terminal) | everything | none |
| Not sent | job, sender no longer allowed | none (terminal) | everything | none (Q6 default) |
| Failed | job after 3 stalled resumes | none (terminal; a new notice is the only retry) | everything | one Error Log row, ids and counts only |

Nothing is reversible. A sent notice cannot be recalled (07 section 0, bad news 3).

## 7 · Permission and visibility matrix

### 7.1 Who sends, and whom they reach (Tier 1)

New function in `hrms/hrms/alvoraa_hr_core/access.py`: `notice_audience_filters(user)`. It never returns `{}` (same discipline as `NO_EMPLOYEES`).

| Sender | Reaches |
|---|---|
| Administrator / System Manager with Notice Sender | Every company (existing helper, unchanged) |
| HR Manager / HR User with Notice Sender | `permitted_employee_filters(user)` unchanged: their companies, narrowed to their branches; an employee with no branch is outside a branch-limited HR user |
| **Director: Notice Sender, no HR role, not System Manager** (Q3=B) | Only companies in their **Company User Permissions**; narrowed by Branch User Permissions if any. **No fallback to their own employee company** (fail closed). With no Company permission: nobody |
| Anyone without Notice Sender | Nothing; every endpoint raises `PermissionError` |

Always AND-ed in: `status = "Active"`, a linked, **enabled** User. A sender whose own Employee record exists and is not Active is refused (lesson 3). The membership test for chosen people is `employee_in_scope`-style list conditions: **never `dict(permitted_employee_filters(), name=X)`** (SEC-3; the CI script in US-23 enforces it). The job always passes `user=<sender>` (SEC-4).

### 7.2 Role × object

| Role | Announcement | Notification Log (own rows) | Expense Claim (portal) | Employee DOB/joining | HR Settings switch |
|---|---|---|---|---|---|
| Employee | none | read own, mark own read | file and read own, see own decline reason | no direct read (level 2); sees colleagues' day/month/years via the endpoint only | none |
| Manager (not approver) | none | own | none beyond own | same as Employee | none |
| Named expense approver | none | own | see and decide claims where they are `expense_approver` | same | none |
| Notice Sender | create, read, write own (Scheduled only) | own | as their other roles | same | none |
| HR Manager | none unless also Notice Sender; sees holders list (names) | own | existing Desk rights (decides in Desk, Q4 default) | existing | change switch |
| System Manager | full | own | existing | existing | change switch; grants and removes Notice Sender |
| Guest | none | none | none | none | none |

### 7.3 Negative cases (who must NOT see or do)

- A plain employee must not see who else got a notice, who read it, the audience, any birth year or age, another person's decline reason, another branch's birthdays (AC-41, 62, 96, 119, 120).
- A Notice Sender must not reach outside scope by editing the request (AC-5 to AC-10), see a per-person read list (AC-39), edit or delete a sent notice (AC-42), cancel or see another sender's notice (AC-37, 43).
- A holder who is neither HR nor System Manager nor given Company permissions reaches nobody (AC-12).
- A manager who is not the named approver must not decide or see a claim; HR is not the approver either (AC-84, AC-82). The claimant must not decide their own claim on any door (AC-91).
- HR Manager must not change a person's opt-out (AC-105) and must not grant Notice Sender unless also System Manager (AC-3).
- A leaver with a working login appears in no audience or birthday list and sends nothing (AC-10, AC-26, AC-98).
- Guest calls nothing (AC-14, AC-62).

## 8 · Working defaults Surbhi can change (01b: she gave no separate answer to Q1, Q2, Q4, Q5, Q6)

These are the security engineer's recommendations, used as defaults. **Change any of them and the listed ACs change.**

| # | Working default | Where it bites | Change it and... |
|---|---|---|---|
| **Q1** | No deletion or purge yet. Temporary debt. The send part is **not released to a live tenant** (DTC) until counsel gives a number for notices and read marks | no code; release gate (US-27) | add a Log Settings row for Notification Log and a purge for Announcement |
| **Q2** | The birthdays switch ships **OFF** on every tenant (explicit default 0). Turned on per tenant only after counsel confirms in writing. The single switch covers birthdays **and** anniversaries (as drawn), so anniversaries are off until then too (the brief said anniversaries on by default; the design's one switch wins) | AC-101, AC-103 | flip the Custom Field default |
| **Q3 = B** | **Decided.** Director reaches only the companies in their Company User Permissions | AC-11 to AC-13 | n/a |
| **Q4** | Only the named approver decides an expense in the portal. HR in scope and stand-ins use Desk | AC-84 | add a second allowed caller, new tests |
| **Q5** | The opt-out text says "on Home". Frappe HR's anniversary emails are not touched and ignore the opt-out | AC-106 | switch those emails off via HR Settings per tenant |
| **Q6** | A notice not sent is marked "Not sent" with the reason. Nobody is alerted | AC-27, AC-35 | add one notification to the sender |

## 9 · Epic and user stories

**Epic E-076:** "Home shows what is waiting, what the office said, and who is celebrating, in a balanced page; people with the access can notify the right group." Each story: INVEST-checked (I ok; N ok; V ok; E ok; S: nothing above 5; T: ACs below).

Risk tier: **T1** / T2 / T3. Points are 1, 2, 3, 5.

| ID | Story | Tier | Pts | Proto / parity rows | SEC / PRIV / OPS | ACs |
|---|---|---|---|---|---|---|
| US-1 | As an **HR Manager** I want the organisation to hold "Notice Sender" as a role it gives and removes in Users, so that sending is a permission, not a rule worked out from levels | T1 | 3 | 33 | SEC-6, OPS-11 | AC-1 to AC-4 |
| US-2 | As the **system** I want to compute whom a sender may reach (HR, director, System Manager), so that no sender reaches outside their scope | T1 | 5 | 22 | SEC-2, SEC-3, SEC-4, PRIV-2 | AC-5 to AC-13 |
| US-3 | As a **Notice Sender** I want to create a notice with limits, so that mistakes and spam are stopped by the server | T1 | 5 | 21-26 | SEC-1, SEC-7, SEC-8, SEC-9, PRIV-3 | AC-14 to AC-22 |
| US-4 | As the **scheduler** I want to send a due notice once, as its sender, in chunks, so that nobody gets it twice and nobody outside scope gets it | T1 | 5 | 23 | SEC-4, SEC-5, SEC-7, OPS-7, OPS-8, OPS-9, OPS-11 | AC-23 to AC-31 |
| US-5 | As a **Notice Sender** I want a stuck or refused send to end in a clear state, so that I know what happened | T1 | 3 | 29 | OPS-9, SEC-21 | AC-32 to AC-35 |
| US-6 | As a **Notice Sender** I want to cancel my scheduled notice, so that a mistake to 240 people can be stopped | T1 | 2 | 30 | SEC-7, SEC-11 | AC-36 to AC-38 |
| US-7 | As a **Notice Sender** I want "Reached N, read by M" for my own notices, so that I know it landed | T1 | 2 | 29 | PRIV-4, SEC-10, OPS-5 | AC-39 to AC-43 |
| US-8 | As a **Notice Sender** I want a Compose page that tells me exactly what will happen, so that I send to the right people | T2 | 5 | 17, 21-29 | PRIV-1 | AC-44 to AC-51, AC-127 |
| US-9 | As a **Notice Sender** at a tenant with email on, I want an email copy option, so that people off the portal also hear | T1 | 3 | 24 | SEC-17, OPS-10 | AC-52 to AC-56 |
| US-10 | As an **Employee** I want one Notices card (announcements pinned, alerts below, unread only) that matches the bell, so that I know what the office told me | T2 | 5 | 12-16 | SEC-9, SEC-18, OPS-3, OPS-4, OPS-6 | AC-57 to AC-65 |
| US-11 | As a **Manager / HR / CXO** I want one Pending card over the inbox, oldest first, so that I see what is waiting and finish it | T2 | 5 | 5, 6, 7, 11 | SEC-19, OPS-1, OPS-2, OPS-4 | AC-66 to AC-73 |
| US-12 | As a **Manager** I want to approve or decline a leave from a sheet, so that I decide without leaving Home | T2 | 2 | 8 | (new: optional reason on `action_leave`) | AC-74 to AC-76 |
| US-13 | As an **Employee** I want my portal expense claim to carry my approver, so that it appears in their Pending list | T1 | 3 | (not drawn) | SEC-12 | AC-77 to AC-79 |
| US-14 | As an **expense approver** I want my claims in my Pending list, so that I can act on them | T1 | 3 | 9 | SEC-16, SEC-19 | AC-80 to AC-83 |
| US-15 | As an **expense approver** I want to approve or decline from a sheet, with a required reason on decline, so that money decisions are quick and explained | T1 | 5 | 9 | SEC-12, SEC-14, SEC-15 | AC-84 to AC-90 |
| US-16 | As **Finance** I want nobody to approve their own claim on any door, so that duties stay separate | T1 | 1 | (not drawn) | SEC-13 | AC-91 |
| US-17 | As an **Employee** I want to see "Declined: <reason>" on my claim, so that a decline is not a dead end | T2 | 2 | 10 | SEC-15 | AC-92 to AC-94 |
| US-18 | As an **Employee** I want to see this month's birthdays and anniversaries in my branch, so that I can say well done | T1 | 5 | 18, 19 | PRIV-5, PRIV-7, OPS-3 | AC-95 to AC-102 |
| US-19 | As an **HR Manager** I want a switch for the birthdays card and a list of who can send, and as an **Employee** a tick to hide myself, so that the organisation and the person stay in control | T1 | 5 | 20, 31, 32 | PRIV-6, PRIV-8, OPS-11 | AC-103 to AC-107 |
| US-20 | As **Surbhi** I want the Activity card and its endpoint removed, so that Home stops recording clicks | T2 | 2 | 1 | SEC-20 | AC-108, AC-109 |
| US-21 | As any **persona** I want a balanced Home at 1280 and 360 px, so that no page has a hole or a tall lonely card | T2 | 5 | 2, 3, 35 | brief section 8 | AC-110 to AC-115 |
| US-22 | As any **persona** I want the Today strip inside the check-in card, so that Pending stays near the top | T3 | 2 | 4 | | AC-116 |
| US-23 | As the **team** I want a CI script that fails on the scope trap and a rising `ignore_permissions` count, so that the trap cannot return | T1 | 2 | | 01c section 9 | AC-117, AC-118 |
| US-24 | (must not) As an **Employee** I must not see who else received or read a notice, or any colleague's decline reason, so that my results and theirs stay private | T1 | 1 | | PRIV-4, SEC-18 | AC-41, AC-62, AC-93, AC-119 |
| US-25 | (must not) As a **Manager who is not the approver**, or the claimant, I must not decide or see a claim, so that money control holds | T1 | 1 | | SEC-12, SEC-13 | AC-84, AC-91, AC-121 |
| US-26 | (must not) As a **colleague** I must not be able to read a birth year or age, so that only day, month and years leave the server | T1 | 1 | | PRIV-5 | AC-96, AC-120 |
| US-27 | As **Surbhi** I want release checks (served file, nginx untouched, no demo file, rollback, measurements), so that a green deploy is proven | T2 | 2 | | OPS-1 to OPS-14 | AC-122 to AC-126 |

**Total: 82 points over 27 stories.** An honest estimate for one engineer plus tests is roughly four to five weeks; Tier 1 stories (about 50 points) also cost an independent review each. No story is above 5.

### YouTrack-ready table (do not import without Surbhi; I create nothing)

| Summary | Persona | Pts | Linked ACs | Linked requirements |
|---|---|---|---|---|
| 076 Notice Sender role + seeding patch | HR Manager | 3 | AC-1..4 | SEC-6 OPS-11 |
| 076 Sender scope function (HR, director, SM) | system | 5 | AC-5..13 | SEC-2..4 PRIV-2 |
| 076 Create notice endpoint with limits | Notice Sender | 5 | AC-14..22 | SEC-1,7,8,9 PRIV-3 |
| 076 Send job (once, as sender, chunks) | scheduler | 5 | AC-23..31 | SEC-4,5,7 OPS-7,8,9,11 |
| 076 Stuck, failed and not-sent states | Notice Sender | 3 | AC-32..35 | OPS-9 SEC-21 |
| 076 Cancel a scheduled notice | Notice Sender | 2 | AC-36..38 | SEC-7,11 |
| 076 Notices I sent: counts only | Notice Sender | 2 | AC-39..43 | PRIV-4 SEC-10 OPS-5 |
| 076 Compose page | Notice Sender | 5 | AC-44..51,127 | PRIV-1 |
| 076 Email copy when email active | Notice Sender | 3 | AC-52..56 | SEC-17 OPS-10 |
| 076 Notices card, sheet, See all, bell | Employee | 5 | AC-57..65 | SEC-9,18 OPS-3,4,6 |
| 076 Pending card over get_inbox | Manager/HR/CXO | 5 | AC-66..73 | SEC-19 OPS-1,2,4 |
| 076 Leave decide sheet + optional reason | Manager | 2 | AC-74..76 | |
| 076 Expense: approver set at filing + backfill | Employee | 3 | AC-77..79 | SEC-12 |
| 076 Expense part in inbox | Approver | 3 | AC-80..83 | SEC-16,19 |
| 076 Expense decide endpoint | Approver | 5 | AC-84..90 | SEC-12,14,15 |
| 076 Expense self-approval hook | Finance | 1 | AC-91 | SEC-13 |
| 076 Decline reason on employee claims screen | Employee | 2 | AC-92..94 | SEC-15 |
| 076 Birthdays endpoint + card | Employee | 5 | AC-95..102 | PRIV-5,7 OPS-3 |
| 076 Birthdays switch, opt-out, holders list | HR/Employee | 5 | AC-103..107 | PRIV-6,8 OPS-11 |
| 076 Remove Activity | Surbhi | 2 | AC-108,109 | SEC-20 |
| 076 Balanced grid + screen test | all | 5 | AC-110..115 | brief 8 |
| 076 Today strip in check-in card | all | 2 | AC-116 | |
| 076 CI scope-trap script | team | 2 | AC-117,118 | 01c 9 |
| 076 Must-not tests (3 stories) | Employee/Manager | 3 | AC-119..121 | PRIV-4,5 SEC-12,13 |
| 076 Release checks | Surbhi | 2 | AC-122..126 | OPS-1..14 |

## 10 · Acceptance criteria

Test type key: **B** = `bench run-tests` test; **D** = DOM test (`run_dom_tests.js`); **S** = real-browser screen test measuring pixels; **R** = review check; **M** = measurement recorded with date and place. Every AC has an observable oracle.

### US-1 Notice Sender role
- **AC-1 (B)** Given a site with two HR Managers, when the seeding patch runs, then exactly one Role `Notice Sender` exists with `desk_access = 0` and both HR Managers hold it. When it runs again, then no User's roles change.
- **AC-2 (B)** Given the role was removed from one HR Manager, when the patch runs again, then that user does not get it back.
- **Changed 28 Oct 2026 (Part B fix pass, Q1 retention gate):** the patch makes the role (desk access 0) and gives it to **nobody**. Sending stays off at every tenant until a System Manager gives the role in Users, after counsel gives a retention number. This replaces Q8 ("HR Managers get it at install") for now. The patch saves no User, so it never removes the Employee role from an HR Manager login with no Employee record. Test: `test_the_patch_makes_the_role_and_gives_it_to_nobody`.
- **AC-3 (B)** Given a user who holds HR Manager but not System Manager, when they save a User with Notice Sender added, then a `PermissionError` is raised. If this passes, it is a finding, not a test to relax.
- **AC-4 (B)** Notice Sender is in no Role Profile and no default role list.

### US-2 Scope
- **AC-5 (B)** Given Branch-A HR (HR User + Branch A User Permission), when they ask for branch B, then the request is refused and no Announcement exists.
- **AC-6 (B)** Given Company-X HR, when they ask for company Y, then refused.
- **AC-7 (B)** Given Branch-A HR chooses "Everyone", when the reach is computed, then only Active, enabled-login people of branch A are counted, and an employee with an empty branch is not.
- **AC-8 (B)** Given a sender with no companies, when they send to one valid id, then refused. (This catches the `dict(..., name=X)` trap.)
- **AC-9 (B)** Given Branch-A HR chooses one A id and one B id, when they send, then the whole request is refused, nothing is written, and the reply gives a count of refused people and no names.
- **AC-10 (B)** Given a chosen id that is a leaver, has no User, or has a disabled User, then the request is refused the same way.
- **AC-11 (B)** Given a director with Notice Sender, no HR role, not System Manager, and Company permissions {X}, when they choose "Everyone", then only X people are counted; a chosen id from Y is refused.
- **AC-12 (B+S)** Given the same director with no Company permission, then the reach is 0, create is refused, and Compose shows "No one is in your scope. Ask HR."
- **AC-13 (B)** Given a System Manager holding Notice Sender, then every company is reachable (documented behaviour).

### US-3 Create
- **AC-14 (B)** Given Guest, a plain employee, and an HR Manager without the role, when each calls create, reach, search, cancel, then `PermissionError` and no record.
- **AC-15 (B)** Empty, whitespace-only, and 301-character messages are refused; exactly 300 after trimming is accepted.
- **AC-16 (B)** More than 25 resolved recipients without `confirmed = 1` is refused; with it, accepted; 25 or fewer needs no confirm.
- **AC-17 (B)** A sender's 6th notice in a tenant calendar day is refused; cancelled and Not sent ones count; two parallel "5th" requests yield exactly one success.
- **AC-18 (B)** Same sender, same text, within 2 minutes returns the first notice; one record, one set of rows.
- **AC-19 (B)** A "Later" time earlier than now (tenant time zone) is refused with "Choose a time that has not passed yet."
- **AC-20 (B)** A message `<img src=x onerror=alert(1)>` is stored in `subject` and `email_content` as `&lt;img...`.
- **AC-21 (B)** After one sent, one cancelled and one held notice, every PRIV-3 field is filled (owner, created, audience kind and value, send time, sent time, reached, email yes/no, status, reason) and a Version row exists for the cancel.
- **AC-22 (B)** `notice_search_people` returns only in-scope Active people with an enabled login, at most 20, name and id only; `notice_reach` returns counts only.

### US-4 Send job
- **AC-23 (B)** Given a notice scheduled by Branch-A HR, when the job function runs with session user Administrator, then only Active branch-A people with logins get a row.
- **AC-24 (B)** Given one due notice, when the job runs twice, then there is exactly one row per recipient.
- **AC-25 (B)** After sending, each row has `type = Alert`, `document_type = Announcement`, `document_name` = the notice, `from_user` = sender, `read = 0`; the notice is Sent with `reached` = row count and `sent_at` set.
- **AC-26 (B)** Given a recipient set to Left and a new joiner added after scheduling, then the leaver gets nothing and the joiner gets a row.
- **AC-27 (B)** Given each of: role removed, User disabled, sender's own Employee not Active, sender no longer has any scope, when the job runs, then nothing is sent and status is Not sent with the reason in words. (SEC-5; 2 of the 4 apply to directors too.)
- **AC-28 (B)** A recipient whose User was deleted is counted as skipped, others receive rows, no Error Log row is written for that.
- **AC-29 (B)** Given 450 recipients, rows are written in chunks of 200 with a commit after each; if the process stops after chunk 1, 200 rows persist.
- **AC-30 (B)** (Changed 28 Oct 2026 by Surbhi: 25, not 200.) "Now" with 25 or fewer recipients finishes in the request: status Sent on return. "Now" with 26 or more returns status Scheduled with `send_at` = now, and a job is enqueued on `long`; the reply says "Sending".
- **AC-31 (B)** One tick takes at most two due notices and only enqueues; it does not write recipient rows itself.

### US-5 Stuck, failed, not sent
- **AC-32 (B)** Given status Sending, last change 11 minutes ago, 300 of 450 rows written, when the next tick runs, then it resumes and the final row count is exactly 450 with no duplicates.
- **AC-33 (B)** After three resumes with no new rows, status is Failed and exactly one Error Log row exists, containing the notice id and counts and no message text, name or email.
- **AC-34 (B)** Given the scheduler did not run for 30 minutes, when it runs, then due notices send in due order; none is lost.
- **AC-35 (B+S)** A Not sent notice shows "Not sent: <reason>" in Notices I sent, and no Notification Log row is created for anyone about it.

### US-6 Cancel
- **AC-36 (B+S)** Given a Scheduled notice, when its owner cancels (dialog "Cancel this notice? It is scheduled but not sent."), then status is Cancelled, a Version row exists, and a later job run writes no rows.
- **AC-37 (B)** Another sender cancelling, or anyone cancelling a Sending or Sent notice, gets a refusal.
- **AC-38 (B)** Cancel and the job racing on one notice end in exactly one outcome.

### US-7 Notices I sent
- **AC-39 (B)** The response keys per notice are exactly: `name, message, audience_label, scheduled_for, status, reason, reached, read, created`. No user, employee or email field anywhere.
- **AC-40 (B)** `reached` and `read` come from one COUNT each on Notification Log by `document_name`; scheduled notices show "Not sent yet"; the list is the sender's own, newest first, at most 20.
- **AC-41 (B)** As a recipient, `get_list("Announcement")` returns nothing and `get_doc` raises `PermissionError`.
- **AC-42 (B)** The owner cannot edit a Sent notice or delete any; delete works for System Manager only.
- **AC-43 (B)** A sender never sees another sender's notice in their list.

### US-8 Compose
- **AC-44 (D)** The counter reads "212 of 300" style live; the hint "Everyone you choose will read this. Do not put pay, health or other personal details in it." is shown.
- **AC-45 (D+B)** Three audience options; the branch/company list shows only what the sender may reach, with counts; the live line reads "This reaches 240 people. Everyone has a login, so everyone sees it. People who have left are skipped."
- **AC-46 (D)** Send later shows date and time and the hint "It goes out at about this time, up to 4 minutes later". The button text is "Send to 240 people" or "Schedule for 3 Nov, 9:00 am to 240 people". Under it: "You have sent 2 of 5 notices today."
- **AC-47 (D)** Above 25: dialog "Send to 240 people?" / "You are about to send this now to 240 people. You cannot take a sent notice back." with "Go back" and "Send to 240 people". 25 or fewer: no dialog.
- **AC-48 (D)** At 5 sent: the form is replaced by "You have sent 5 notices today." and "That is the limit for one day. You can send again tomorrow."
- **AC-49 (D)** Errors appear at the field with the exact texts in 02-design 6.8, focus moves to the field, `aria-describedby` is set.
- **AC-50 (D)** After sending: green line "Sent to 238 people. They will see it on Home and in the bell." and Notices I sent shows "Reached 238 people · Read by 212 of 238".
- **AC-51 (D)** "Send a notice" is absent (not greyed) for non-holders; the server refusal in AC-14 still holds.
- **AC-127 (R)** The warning line is listed as "guidance", never as a safeguard, in the spec's control table and any customer answer (PRIV-1).

### US-9 Email copy
- **AC-52 (D)** The email control is absent when email is not active and present, unticked, when it is.
- **AC-53 (B)** `email = 1` when email is not active is refused at create.
- **AC-54 (B)** Scheduled with email on, then email muted, then the job runs: rows written, zero Email Queue rows, `email_note` = "email not sent: email is off".
- **AC-55 (B)** A recipient with email notifications on and no tick gets zero Email Queue rows.
- **AC-56 (B)** With email active and ticked, Email Queue rows are queued after the bell rows in the same chunk, escaped, and no message text appears in any log.

### US-10 Notices card
- **AC-57 (D)** The card shows unread only, announcements first marked "Pinned" with sender label and time, then alerts, at most 5; chip reads "N unread".
- **AC-58 (B)** For three users with different data, the chip number equals the bell badge number, including with a scheduled send mid-run. Both come from the one function.
- **AC-59 (B+D)** Tapping a row opens a sheet with the full text and marks it read through Frappe's `mark_as_read`; it leaves the card.
- **AC-60 (D)** See all lists the last 30 days with "Read" marks; the bell opens the same sheet.
- **AC-61 (D)** Empty states: "You are up to date." / "No new notices. Older ones are under See all." and "No notices." / "Messages from HR and management, and alerts about your work, appear here."
- **AC-62 (B)** User B marking user A's row leaves A's row unread; Guest is refused; only a fixed field list is returned.
- **AC-63 (D)** Text `<img src=x onerror=alert(1)>` shows as literal text, with no `img` or `script` element, on the card, sheet, See all and Notices I sent.
- **AC-64 (B+M)** Unread list and bell count each take one query regardless of headcount; `EXPLAIN` on 100,000 Notification Log rows is recorded; an index is added only if it shows a scan.
- **AC-65 (D)** If a card fails to load it shows "We could not load this. Try again" with a button; a skeleton appears within 300 ms.

### US-11 Pending
- **AC-66 (B)** Home gets Pending from `get_inbox`; a grep test finds no second Pending filter.
- **AC-67 (D+B)** At most 5 rows, oldest `waiting_since` first across kinds; row line 1 person (or policy/request), line 2 kind, detail and "waiting N days"; "Review" or "Open" button; whole row tappable.
- **AC-68 (B)** Each part's row keys are exactly the old set plus `waiting_since`; `get_nav_counts` total still equals the sum of parts including expenses.
- **AC-69 (D+B)** A CXO sees one row per kind with a count and no people.
- **AC-70 (D)** Empty: "Nothing waiting on you." / "Requests that need you, and policies to read, appear here." See all shows at most 50 rows per kind and count equals rows.
- **AC-71 (B)** Existing inbox tests (no absence reasons, no others' notes, no document ids in counts) pass unchanged.
- **AC-72 (M)** Home query count is the same at 500 and 5,000 employees; `get_inbox`, notices and birthdays each p95 at or under 500 ms; before/after of the old Home recorded. If `get_inbox` misses, add a `limit` argument first (OPS-2a); a cache only after a recorded miss.
- **AC-73 (D)** Home calls fire together; each card has its own skeleton and failure box.

### US-12 Leave sheet
- **AC-74 (D)** The sheet shows name, "Leave request", type, dates, days. Approve calls `action_leave(..., "approve")`. Decline requires 1 to 140 characters before the button becomes "Send decline"; no reason, no decline.
- **AC-75 (B)** `action_leave` accepts an optional `reason`; when given it is validated 1 to 140 and saved as a Comment on the Leave Application; callers that pass none behave as today; a non-approver and the claimant are refused as today.
- **AC-76 (D)** After a decision the decided row leaves the card and the bell updates.

### US-13 Approver at filing
- **AC-77 (B)** A claim filed through `apply_expense_claim` has `expense_approver` = the Employee's, else the Department's first expense approver, and is shared with that approver.
- **AC-78 (B)** With neither, the claim is filed with an empty approver; no error; the count of such claims is reported.
- **AC-79 (B)** The backfill patch sets the approver on open Draft claims with an empty approver using `doc.save` (so the share is made), reports "set N, unresolvable M", and a second run changes nothing.

### US-14 Expense in inbox
- **AC-80 (B)** Part `expense_approvals` has a non-empty scope string and filters `expense_approver = caller`, `docstatus = 0`, `approval_status = "Draft"`, `employee != caller's`; uses `get_list`; cap 50; count equals rows.
- **AC-81 (B)** Row keys are exactly `name, employee_name, expense_type, expense_date, amount, note, waiting_since, action`.
- **AC-82 (B)** A plain employee and an HR Manager who is not the approver get count 0; Guest refused; a caller with no Active Employee gets `no_rows()`.
- **AC-83 (B)** The existing inbox tests run over the new part with at least one portal-filed claim with an approver in the test data (PPJ has none, so "0 rows" proves nothing there).

### US-15 Expense decision
- **AC-84 (B)** A caller who is not the claim's `expense_approver` (including HR) gets `PermissionError`; the claim is unchanged.
- **AC-85 (B)** An approver whose Employee is not Active is refused.
- **AC-86 (B)** Approve sets `docstatus = 1`, `approval_status = "Approved"`, via `doc.submit()`; a GL Entry exists. A grep test finds no `ignore_permissions`, `db_set` on status, or raw SQL in `decide_expense`.
- **AC-87 (B)** Decline needs a reason of 1 to 140 characters (else refused); stores it in `alvoraa_decline_reason`; `approval_status = "Rejected"`, `docstatus = 1`; no GL Entry.
- **AC-88 (B)** Approve twice returns "already decided" with one set of GL entries; approve and decline at once: one wins.
- **AC-89 (D)** Reason `<b>x</b>` shows as text.
- **AC-90 (D)** The sheet shows the amount large, "Waiting 8 days. Approving passes it to accounts for payment. You cannot take it back here."; toasts "Approved. Pooja Mishra's claim of ₹2,300 goes to accounts." and "Declined. Pooja will see your reason." (names and amounts are the claim's).

### US-16
- **AC-91 (B)** An employee who is their own approver is refused on approve through the portal, `doc.submit()` and REST, with HR Settings `prevent_self_expense_approval = 0`.

### US-17
- **AC-92 (D)** The employee's claim row shows "Declined: <reason>", escaped.
- **AC-93 (B)** Employee B's `get_expense_claims` never returns A's reason.
- **AC-94 (B)** The claim title still comes from `remark`; the reason is not written to it.

### US-18 Birthdays
- **AC-95 (B)** Each row's keys are exactly `display name, kind, day, month` plus `years` for anniversaries. No id, date, year, age or photo.
- **AC-96 (B)** No response value matches a four-digit year or equals any seeded `date_of_birth` or `date_of_joining`.
- **AC-97 (B)** The viewer's own Active Employee gives company and branch; a viewer with no branch or no Active Employee gets an empty list; branch-A viewer never sees branch B or an employee with no branch.
- **AC-98 (B)** Leavers, people with no date and opted-out people are excluded; a person set to Left disappears.
- **AC-99 (D)** At most 5 rows, today and coming days first, then earlier days marked "earlier this month"; "See all N" opens the whole month; empty: "No birthdays or anniversaries this month." / "People in your branch who share these dates appear here."
- **AC-100 (B)** Years = completed years, at least 1; someone who joined this year is not shown as an anniversary `[ASSUMPTION]`. A 29 Feb birthday shows on 28 Feb in a non-leap year `[ASSUMPTION]`.
- **AC-101 (B)** Switch off: empty list and zero Employee queries (query counter); the card is absent and the grid reflows.
- **AC-102 (B+M)** One query, with branch, status, opt-out and month filters in SQL; 5,000 employees in one branch is timed and its payload size recorded.

### US-19 Switch, opt-out, holders
- **AC-103 (B)** After the patch, `alvoraa_birthdays_on_home = 0` on every tenant. Only HR Manager or System Manager can change it (others `PermissionError`); the change appears in Version history; the page shows "Last changed by <name>, <date>".
- **AC-104 (D)** Switching off shows "Switch off birthdays and anniversaries? Home will stop showing this card for everyone in the organisation (412 people)." with "Keep it on" and "Switch off"; switching on is one tap.
- **AC-105 (B)** `set_birthday_hide` takes no employee argument and changes only the caller's own record; an HR Manager saving that field on someone else in Desk is refused or ignored.
- **AC-106 (D)** The tick reads "Show my birthday and work anniversary on Home to colleagues in my branch" with "They see your name, the day and month, and your years of service. Never your age or birth year. You can change this at any time." **(wording differs from the drawing by "on Home"; Q5 working default; needs Surbhi's yes).** When the switch is off the tick is hidden and the page says "There is nothing to set here right now."
- **AC-107 (B)** (Changed 28 Oct 2026 by Surbhi, to match the prototype.) `notice_sender_holders` works for HR Manager or System Manager only; each row is the full name, the job title, and who last changed that person's Notice Sender access and on which date (from the User's own history). No email, no user id. A plain employee or an HR User is refused.

### US-20 Remove Activity
- **AC-108 (B+D)** `grep -rn get_portal_activity` returns nothing outside `docs/`; `homeActivity` and `renderActivityFeed` are gone; Home shows no Activity card; a call to the old method returns "not found".
- **AC-109 (B)** The `ignore_permissions` count in the CI script falls by 3 and Home still loads.

### US-21 Balance (measurable, measured by a real-browser test on the real cards)
- **AC-110 (S)** At 1280 px the grid content is 992 px with two 488 px columns and a 16 px gap; cards in a row have equal height; a hidden card drops out and the rest reflow; a lone last card spans full width; there is no fixed 300 px column.
- **AC-111 (S)** Card order is identical for everyone (02-design section 3 table). At 360 px: one column, 328 px cards, order check-in, Pending, Notices first.
- **AC-112 (S)** For each cell below: largest gap between cards is at most 24 px; the two columns end within 120 px of each other; no card is more than 2 times the median card height on that page; every list shows at most 5 rows; no horizontal scroll; every pair in a row is within 1.5 times, or the shorter stretches to match and the readout names that pair with its natural ratio.
- **AC-113 (S)** The three new cards show their plain sentence when empty and are never hidden (exception: Birthdays when the switch is off). Goals, Team goals, Documents and Policies still hide when empty and the grid shows no hole.
- **AC-114 (S)** The cell set is: 5 personas (Employee, Frontline, Manager, HR Manager, CXO) × data none / few / 200 rows × 1280 and 360 px × birthdays on and off = 60 cells, 0 failures. The prototype's own run (60 cells, 0 failures, tallest card 467 px, closest call 2.0x) is the target; the prototype used stand-in existing cards, so the median must be re-measured on the real ones. `[UNVERIFIED]` which browser runner the repo already has; if none, the engineer states what is added.
- **AC-115 (D+R)** Accessibility from 02-design section 9: each card a section with a heading; rows real buttons (Enter, Space); 3 px focus ring; sheets `role=dialog`, `aria-modal`, focus in, Escape closes, focus returns; colour never the only signal; tap targets at least 44 px on a phone, rows at least 56 px; field text 16 px; nothing under 12 px; bell accessible name "Notices, 20 unread"; switch has a name and "On"/"Off" in words.

### US-22
- **AC-116 (S)** The Today strip is inside the check-in card, not a separate card; Pending and Notices follow the check-in card on a phone.

### US-23 CI script
- **AC-117 (CI)** `scripts/check_scope_traps.py` fails on `dict(permitted_employee_filters(` with `name=` and on `{**permitted_employee_filters(`; `--self-test` proves it fails on a bad sample.
- **AC-118 (CI)** It fails if the `ignore_permissions` count in `alvoraa_portal/` and `hrms/hrms/alvoraa_hr_core/` (non-test) is above the stored number (289 before this slice; the slice stores the lower number, then the number can only go down).

### Must-not stories (also covered above)
- **AC-119 (B)** Given employees A and B in one branch, B cannot read A's Notification Log rows, the audience of A's notices, or any read list.
- **AC-120 (B)** A colleague cannot read `date_of_birth` or `date_of_joining` through the Employee API (field rights unchanged), and the birthdays endpoint is the only path.
- **AC-121 (B)** `get_expense_claims` returns only the caller's own claims; a guessed claim id on the decide endpoint gets `PermissionError` (AC-84).

### US-27 Release checks
- **AC-122 (M)** After deploy to dev, the served `portal.js` contains a string only the new version has (fetched, not assumed from a green deploy).
- **AC-123 (R)** The diff does not touch `deploy/nginx.conf`; no `demo/` file lands on `main`.
- **AC-124 (R)** Before main: the previous image tag exists in the `alvoraa-app` package; any Scheduled notices are cancelled first or Surbhi accepts that they go out late (they never send while old code runs).
- **AC-125 (M)** The 07 section 4 measurements are recorded with date and place: Home queries at 500 and 5,000; p95s; 1,200-recipient send (time, commits, memory); kill-and-resume; `EXPLAIN`; birthdays worst case; bell equals chip mid-send.
- **AC-126 (M)** A "Send later" test on dev takes about a minute (dev tick 60 s); the production tick (3 to 4 minutes) is noted from config, not changed.

## 11 · Edge cases (only ones that happen)

| Case | Rule |
|---|---|
| Scheduled for Monday, sender leaves Friday | Job refuses; Not sent (AC-27) |
| Recipient moves branch between scheduling and sending | Audience resolved at send, so the new branch decides (AC-26) |
| Employee with no login or disabled User | Never counted, never an error (AC-10, AC-28). Staff all have logins (01b D3 update) |
| Person with no manager / no branch | Branch-limited HR does not reach them (DEF-6); a branch-less viewer sees no birthdays (AC-97) |
| Two HR users send the same text | The 2-minute repeat rule is per sender, so both go. Intended |
| Double tap / network retry on Send | Same text within 2 minutes returns the first notice (AC-18). "May have gone through" wording was not drawn: open decision 10 |
| Worker killed mid-send | Resume by skipping people who already have a row (AC-32) |
| Cancel in the same second the job starts | Row lock; one wins (AC-38) |
| Daily limit across midnight | Tenant calendar day; cancelled ones count (AC-17) |
| Time zones / DST | `send_at` is tenant time; the job compares with the tenant "now" |
| Claim approver is the claimant | Never in their own Pending; refused (AC-80, AC-91) |
| Claim approver changed after filing | The inbox follows the field as it is now; HR changes it in Desk and the share follows the save |
| Approver leaves | Their claims are not decidable in the portal; HR re-assigns in Desk |
| Claim cancelled or already paid | Only `docstatus 0` and Draft show (AC-80) |
| Birthday: joined this year, 29 Feb, 200 birthdays in a month | Not an anniversary; 28 Feb; five rows and "See all N" (AC-99, AC-100) |
| Opted-out person is also the viewer | Still sees others; only their own row is hidden |
| Re-hired employee | Counted by their current Active record; `date_of_joining` as stored |
| Multi-company tenant | Birthdays and notices stay inside company and branch; director inside Company permissions |
| Bulk: 1,200 recipients | Chunks of 200 (AC-29); measured (AC-125) |
| Concurrent approvals of one claim | Row lock; one decision (AC-88) |

## 12 · Non-functional numbers for this slice

From `nfr-budget.md` and 07: API p95 at or under 500 ms; phone page at or under 2.5 s; query count flat from 20 to 5,000 people; skeleton within 300 ms.

| Item | Number |
|---|---|
| Tenants | 1 to 5,000 employees per tenant; DTC about 442 |
| Notice rows | one per recipient per notice; up to 1,200 for a CXO send; weekly sends at 5,000 employees give tens of thousands of rows a month |
| Home list sizes | 5 rows per card; See all up to 50 per kind |
| Send job | chunks of 200, commit per chunk, at most 2 notices per tick, on `long`; a 1,200-person send under about 10 s (estimate, measured at AC-125) |
| Resume | Sending older than 10 minutes; Failed after 3 stalled resumes |
| Read counts | one COUNT per notice, only on Notices I sent, never on Home |
| Home payload | the three cards under about 5 KB (estimate) |
| Cache | none. A 30 to 60 s cache on Pending only if a recorded measurement misses the budget (OPS-2b) |
| Retention | open (Q1). No purge in this slice. Debt recorded |
| Personal data | message (internal, may carry personal data), recipient rows, day and month and years (sensitive, computed on read, not stored again) |

## 13 · Migration and backfill for existing tenants

| Item | What happens | Safe to run twice? | Rollback |
|---|---|---|---|
| `Announcement` DocType | arrives with `bench migrate` | yes | table sits unused with old code |
| Custom Fields (3) | `after_migrate` `create_custom_fields` | yes | fields sit unused |
| `Notice Sender` role + grant to current HR Managers (Q8) | patch listed in `patches.txt`, runs after the DocType exists; grants only to users who hold HR Manager at that moment; never again | yes (AC-1, AC-2) | not reversed; harmless without the code |
| Birthdays switch | explicit `0` | yes | n/a |
| Open expense claims without an approver | patch (AC-79) via `doc.save` | yes | none needed; approver field can be cleared by hand |
| Existing Notification Log rows | untouched | n/a | n/a |
| `inbox_api` six-part tests | updated deliberately to seven | n/a | n/a |
| Dry run | on a copy per `REHEARSAL.md`; `[UNKNOWN]` if a large-tenant copy exists | | |

Nothing is seeded on production (no `demo/` file).

## 14 · Notifications and messages

| Message | Trigger | Recipient | Copy | Never contains |
|---|---|---|---|---|
| Notice | job writes row | each recipient | the sender's text, plain, in a Notification Log row of type **Alert** | audience, other recipients, read status |
| Email copy | tick + email active | recipient | same text, escaped | sent only when both true (AC-52 to AC-56) |
| Toasts, errors, dialogs, empty states | screens | the user | exact strings quoted in the ACs above, taken from 02-design | names of out-of-scope people; leave reasons |
| Not sent / Failed | job | nobody is notified (Q6); the sender sees it in Notices I sent; Failed adds one Error Log row | ids and counts | message text, names, emails |
| Expense decision | decide | the claimant sees it on the claims screen; Frappe HR's own notify on status change is unchanged `[UNVERIFIED how it behaves at DTC]` | | the approver's private notes |

Email is off at DTC now, so nothing emails there. No new email template is added.

## 15 · Localisation and accessibility

English only for notice text (D7). Screen words are written as whole sentences with values passed in (`_("...")`, and `__()` in JS) so they can be translated later; Hindi runs about 30 percent longer and rows clip with "…" with the full text one tap away. Dates "29 Oct" in cards and "3 Nov, 9:00 am" with a time. Currency with the ₹ sign and the claim's currency. Accessibility is AC-115. Frontline on a 360 px phone: one column, bottom sheets, 44 px targets, one short sentence per notice, no hover-only control.

## 16 · Audit and traceability of records

| Question a year later | Answered by |
|---|---|
| Who sent what, to which audience, when, to how many | `Announcement` (owner, creation, audience fields, send time, reached) with Track Changes |
| Who cancelled, and when | Version row on the Announcement |
| Did a person get it | their own Notification Log row (the sender sees counts only) |
| Why was it not sent | `status_reason` |
| Who gave Notice Sender to whom | `[UNVERIFIED]` whether User role changes are in Version on this site (01c section 11). Engineer checks; if not, it is a known gap |
| Who decided an expense | Expense Claim submit history, `modified_by`, GL Entry; reason in `alvoraa_decline_reason` |
| Who changed the birthdays switch | HR Settings Version |
| Refusals | `access.log_refusal` rule ids, never message text (SEC-21) |

## 17 · Compliance-impact sub-analysis (I am not a lawyer)

### 17.1 Data touched
| Field / object | Class | Purpose | Lawful basis (as recorded) | New? |
|---|---|---|---|---|
| Notice message | internal; may carry personal data despite the warning | tell staff something | employer's duty to inform (brief); not recorded as a legal basis | yes |
| Audience, chosen ids | internal | send to the right people | same | yes |
| Notification Log `for_user`, `read` | personal | deliver and give a count | same | partly (read flag exists; new use) |
| Day, month of birth; day, month, years of service | **sensitive** (level 2 fields) | birthday card | **counsel oral OK only** (01b D10) | new use, no new collection |
| Opt-out tick | personal preference | honour choice | the person's own choice | yes |
| Decline reason (140) | personal | tell the claimant why | existing claim processing | yes |

Minimisation: no new personal data is collected except the opt-out and the decline reason. The outcome is impossible without both.

### 17.2 Obligations engaged
| Obligation | Source | What this slice does | Feature |
|---|---|---|---|
| Purpose limitation, minimisation | DPDP (baseline section 2, 24 Aug 2026) | day, month, years only leave the server | AC-95, AC-96 |
| Notice / consent or legitimate use for birthdays | DPDP | switch off by default; opt-out; wording | AC-101, 103, 106 |
| Storage limitation | DPDP, counsel "not for ever" | **gap**: no number yet | Q1 debt; release gate |
| Reasonable security safeguards | DPDP | scope, escape, audit | SEC items |
| Segregation of duties on expenses | compliance map F1/B7 | self-approval hook | AC-91 |
| Logs without personal data | CERT-In | ids and counts only | AC-33 |

The compliance-feature map was checked: no existing feature discharges these; nothing here re-specifies one.

### 17.3 Visibility delta
New: colleagues in the same branch see a person's name, day, month and years of service (only if the switch is on and they have not opted out). A sender sees counts. An approver sees claim amounts of their own reports (already true in Desk). **Not new and must stay so:** nobody sees birth year, age, a read list, another branch, or another sender's notice.

### 17.4 Decision automation
No decision about a person is made or influenced by the system. A sender chooses recipients; an approver decides a claim; the system only enforces scope and counts. No AI. None of the prohibited capabilities is needed (the removed Activity card was the nearest to passive monitoring and is deleted).

### 17.5 Retention and deletion
Notices, rows, read marks: kept until a counsel number exists (Q1, debt). Birthdays: nothing stored. Opt-out: life of the Employee record. Decline reason: with the claim. Erasure of an employee leaves their Notification Log rows to the existing rules; no change is made here. Nothing else changes.

### 17.6 ⚠ Open compliance questions
| Question | Who decides | Blocks |
|---|---|---|
| ⚠ COMPLIANCE How long to keep notices, recipient rows and read marks (Q1) | Surbhi with counsel | release of the send part to a live tenant |
| ⚠ COMPLIANCE Written confirmation for birthdays shown by default with opt-out (Q2) | Surbhi with counsel | turning the switch on at DTC |
| ⚠ COMPLIANCE Is a "read" mark personal data needing its own period (brief section 10) | Surbhi with counsel | same as Q1 |
| Anniversary emails ignore the opt-out (Q5) | Surbhi | wording only |
| Residual risks in 01c section 12 are all **not yet accepted** | Surbhi | push to dev |

### 17.7 AI
None.

## 18 · Parity table (02-design.md section 14, all 35 rows)

"Differs" means the build would not match the drawing exactly and needs Surbhi's yes first.

| # | Feature | Story | ACs | Built as drawn? |
|---|---|---|---|---|
| 1 | Activity removed | US-20 | 108, 109 | yes |
| 2 | Row-based grid, no 300 px column | US-21 | 110 | yes |
| 3 | Phone order | US-21 | 111 | yes |
| 4 | Today strip in check-in | US-22 | 116 | yes |
| 5 | Pending: 5 rows, chip, See all, empty | US-11 | 67, 70 | yes |
| 6 | Row text, Review/Open, days, oldest first | US-11 | 67, 68 | yes |
| 7 | CXO counts | US-11 | 69 | yes |
| 8 | Leave sheet | US-12 | 74 to 76 | yes **plus** the optional reason on `action_leave` (not visible on screen) |
| 9 | Expense sheet | US-15 | 86 to 90 | yes |
| 10 | Decline reason on employee screen | US-17 | 92 | yes |
| 11 | Pending See all | US-11 | 70 | yes |
| 12 | Notices card | US-10 | 57, 58 | yes |
| 13 | Notice sheet | US-10 | 59 | yes |
| 14 | See all, 30 days | US-10 | 60 | yes |
| 15 | Bell opens same sheet | US-10 | 58, 60 | yes. **Consequence:** the bell number now counts unread notices only (open decision 2) |
| 16 | Notices empty states | US-10 | 61 | yes |
| 17 | Send a notice only for holders | US-8 | 51 | yes |
| 18 | Birthdays card | US-18 | 99 | yes |
| 19 | Absent when switch off | US-18 | 101 | yes |
| 20 | Opt-out tick | US-19 | 106 | **Differs: "on Home" added (Q5 default)** |
| 21 | Compose message, warning | US-8 | 44 | yes |
| 22 | Audience with live line | US-8 | 45 | yes |
| 23 | Now or later, 4-minute hint | US-8 | 46 | yes |
| 24 | Email tick | US-9 | 52 | yes |
| 25 | Button naming the action, sent-today line | US-8 | 46 | **Differs for Now over 200: "Sending" instead of "Sent" (open decision 1)** |
| 26 | Confirm above 25 | US-8 | 47 | yes |
| 27 | 5-a-day screen | US-8 | 48 | yes |
| 28 | Inline errors | US-8 | 49 | yes |
| 29 | Result line, Notices I sent | US-8, US-7 | 50, 39, 40 | yes (same open decision 1 for over 200) |
| 30 | **Cancel a scheduled notice (IN)** | US-6 | 36 to 38 | yes |
| 31 | Org settings holders list | US-19 | 107 | yes |
| 32 | Org settings switch, confirm off | US-19 | 103, 104 | yes |
| 33 | Role given in Users | US-1 | 1 to 4 | yes |
| 34 | Scaffolding (tags, banner, review bar, readout) | | | no, by design (the readout becomes the screen test, AC-114) |
| 35 | Existing cards unchanged | US-21 | 113 | yes |

## 19 · Traceability

### 19.1 Brief and Surbhi's decisions

| Source | Item | Story | ACs | Test | Status |
|---|---|---|---|---|---|
| Brief 8.1 | Remove Activity | US-20 | 108, 109 | B, D | covered |
| Brief 8.2 | Pending over `get_inbox` | US-11 | 66 to 73 | B, D, M | covered |
| Brief 8.3 | One Notices card, 5 rows, count = bell | US-10 | 57 to 65 | B, D | covered |
| Brief 8.4 | Announcement record, 300 chars, now/later, status | US-3, US-4 | 14 to 31 | B | covered |
| Brief 8.5 | Audience: all in scope, company/branch, chosen | US-2, US-8 | 5 to 13, 45 | B, D | covered |
| Brief 8.5a | Birthdays widget | US-18 | 95 to 102 | B, D | covered |
| Brief 8.6 | Scheduler sends | US-4 | 23 to 31 | B | covered |
| Brief 8.7 | Sent and read counts, no names | US-7 | 39 to 43 | B | covered |
| Brief 8.8 | Balance rule | US-21 | 110 to 114 | S | covered |
| Brief 8 "before ship" | Server scope, tests for branch, company, guest, leaver, double send | US-2, US-3, US-4 | 5, 6, 10, 14, 24 | B | covered |
| Brief 4a | Senders HR + management; line managers and employees never | US-1, US-2 | 1 to 4, 14 | B | covered |
| Brief 10 | Spam / confirm / daily limit | US-3, US-8 | 16, 17, 47, 48 | B, D | covered |
| Brief 10 | Sender's right re-checked at send | US-4 | 27 | B | covered |
| Brief 10 | Double send | US-4 | 24 | B | covered |
| Brief 10 | 10x data chunking | US-4 | 29, 125 | B, M | covered |
| Brief 10 | Bell and card show one number | US-10 | 58 | B | covered |
| Brief 10 | Nobody holds the role for the branch: no Send button | US-8, US-2 | 12, 51 | B, D | covered |
| Brief 11 | Success measures (read share, balance test) | US-7, US-21 | 40, 114 | B, S | covered. Request-to-decision time: no new tracking, measured from existing dates; not an AC |
| D1 | Pending on existing inbox | US-11 | 66 | B | covered |
| D2 | 25 and 5 a day | US-3 | 16, 17 | B | covered (constants, not settings; assumption A5) |
| D3 | Staff with no login out; later "all have logins" | US-2 | 10 | B | covered |
| D4 | Email only when active | US-9 | 52 to 56 | B, D | covered |
| D5 | Managers approve expenses in Pending | US-13 to US-17 | 77 to 94 | B, D | covered |
| D6, D11 | Empty cards short sentence | US-21 | 113 | S | covered |
| D7 | English only | section 15 | none (no code) | R | covered by decision |
| D8 + simplified | Role-based senders, not computed | US-1, US-2 | 1 to 13 | B | covered |
| D9 | One Notices card | US-10 | 57 | D | covered |
| D10 | Birthdays: switch, opt-out, branch, no age | US-18, US-19 | 95 to 107 | B, D | covered |
| 01b design approved | Q1 to Q8 of the design | see parity | | | covered; Q6 (oldest first key) AC-68; Q7 AC-87, 92; Q8 AC-1 |
| 01b security Q3=B | Director reaches own Company permissions | US-2 | 11, 12 | B | covered |
| 01b Q1, Q2, Q4, Q5, Q6 | Working defaults | section 8 | 17.x, 84, 101, 106, 27, 35 | B | covered as defaults, awaiting her word |

### 19.2 Design (02-design.md)

| Source | Item | Story | ACs | Status |
|---|---|---|---|---|
| Sections 3, 4, 5, 6, 7 | Grid, cards, expense sheet, compose, org settings | US-8 to US-22 | as parity table | covered |
| Section 9 | Accessibility | US-21 | 115 | covered |
| Section 11 | Skeleton and failure box per card | US-10, US-11 | 65, 73 | covered |
| Section 11 | "May have gone through" on send timeout | none | none | **gap by design: needs Surbhi's yes (open decision 10)** |
| Section 15 items 1 to 8 | Analyst list | US-21, 11, 15, 10, 18, 3, 1, 21 | 114, 66 to 73, 84 to 90, 57 to 65, 95 to 102, 14 to 22, 1 to 4, 115 | covered |
| Section 16 | Usability test plan (5 people, phone) | none | none | not an AC; the test engineer runs it at the design check; listed here so it is not lost |
| Section 18 | Own pending claim in Pending, WhatsApp, templates, repeat reminders, who-has-not-read, Hindi | none | none | not in this slice (Surbhi's design decision) |

### 19.3 Security and privacy (01c)

| ID | Story | ACs | Test | Status |
|---|---|---|---|---|
| SEC-1 | US-3 | 14 | B | covered |
| SEC-2 | US-2 | 5 to 7, 11 to 13 | B | covered |
| SEC-3 | US-2, US-23 | 8 to 10, 117 | B, CI | covered |
| SEC-4 | US-4 | 23 | B | covered |
| SEC-5 | US-4 | 27 | B | covered |
| SEC-6 | US-1 | 1 to 4 | B | covered |
| SEC-7 | US-3, US-4, US-6 | 18, 24, 36, 38 | B | covered |
| SEC-8 | US-3 | 15 to 17 | B | covered |
| SEC-9 | US-3, US-10 | 20, 63 | B, D | covered |
| SEC-10 | US-7 | 41, 42 | B | covered |
| SEC-11 | US-6 | 37 | B | covered |
| SEC-12 | US-13, US-15 | 77, 84, 85 | B | covered |
| SEC-13 | US-16 | 91 | B | covered |
| SEC-14 | US-15 | 86, 88 | B | covered |
| SEC-15 | US-15, US-17 | 87, 89, 92, 93 | B, D | covered |
| SEC-16 | US-14 | 80 to 83 | B | covered |
| SEC-17 | US-9 | 52 to 56 | B | covered |
| SEC-18 | US-10 | 62 | B | covered |
| SEC-19 | US-11 | 68 | B | covered |
| SEC-20 | US-20 | 108, 109 | B | covered |
| SEC-21 | US-5 | 28, 33 | B | covered (decide-endpoint errors follow the same rule; engineer adds one test) |
| PRIV-1 | US-8 | 127 | R | covered |
| PRIV-2 | US-2 | 7, 10, 23, 26 | B | covered |
| PRIV-3 | US-3 | 21 | B | covered |
| PRIV-4 | US-7 | 39 | B | covered |
| PRIV-5 | US-18 | 95, 96, 120 | B | covered |
| PRIV-6 | US-19 | 101, 103, 105, 106 | B, D | covered |
| PRIV-7 | US-18 | 97, 98 | B | covered |
| PRIV-8 | US-19 | 107 | B | covered |
| 01c section 9 | CI script | US-23 | 117, 118 | CI | covered |
| 01c section 10 | test data needs (two branches; portal-filed claim with approver; birthdays in two branches; email-on recipient) | all B stories | 5, 83, 97, 55 | B | covered as fixture requirements |

### 19.4 DevOps (07)

| ID | Story | ACs | Test | Status |
|---|---|---|---|---|
| OPS-1 | US-11 | 72 | M | covered |
| OPS-2 | US-11 | 72 | M | covered |
| OPS-3 | US-10, US-18 | 64, 102 | B, M | covered |
| OPS-4 | US-10, US-11 | 65, 73 | D | covered |
| OPS-5 | US-7 | 40 | B | covered |
| OPS-6 | US-10 | 64 | M | covered (index only if EXPLAIN shows a scan) |
| OPS-7 | US-4 | 29, 31 | B | covered |
| OPS-8 | US-4 | 24 (and row lock in 38) | B | covered, adapted: skip-existing check instead of a unique key on a Frappe table |
| OPS-9 | US-5 | 32 to 34 | B | covered |
| OPS-10 | US-9 | 54, 56 | B | covered |
| OPS-11 | US-1, US-19, section 13 | 1, 2, 103 | B | covered |
| OPS-12 | US-27 | 122, 123 | M, R | covered |
| OPS-13 | US-27 | 124 | R | covered |
| OPS-14 | US-27 | 126 | M | covered (the local to dev to main path is CLAUDE.md section 1; Surbhi decides each push) |
| 07 section 4 | measurements | US-27 | 125 | M | covered |

**Gaps listed:** the design section 11 "may have gone through" line (not drawn, needs her yes), the design section 16 usability test (not an AC), brief section 11 first measure (no new tracking). Nothing else is without an AC.

## 20 · Smaller first release and honest size

**Full spec: 82 points, 27 stories.** About half of it (the 50 points of Tier 1) is the sending, expense and birthday work. If it is too big, this is how I would cut it. Parity still means each part, when built, is built as drawn. This only changes the order. It needs Surbhi's yes because she approved one release.

| Release | Contents | Stories | Points | Tier |
|---|---|---|---|---|
| **A · Home** | Activity removed, balanced grid, Today strip, Pending (leave, goals, attendance, shift, policies, own requests), leave sheet, Notices card showing alerts only (no sender yet), bell = chip | US-10 (alerts only, no announcement code), US-11, US-12, US-20, US-21, US-22, US-23 | about 28 | 2 |
| **B · Send** | Role, scope, create, job, compose, cancel, counts, email copy | US-1 to US-9 | about 33 | 1 |
| **C · Money and people** | Expense approval in Pending, birthdays, opt-out, switch | US-13 to US-19, US-24 to US-26 | about 25 | 1 |

A gives Surbhi the balanced page and the Pending list at once, with no money and no personal data. B needs the Q1 retention number before a live tenant. C needs Q2 in writing before the birthdays switch is turned on, and the expense work is the riskiest code. US-27 is split across all three.

## 21 · Subtract pass

Removed from my own spec and from the inputs: the **Draft** state (nothing reads it); cancelled-by and cancelled-at fields (Version does it); a recipient child table (Notification Log rows are the recipients); a read counter field (a COUNT does it); a unique key on Notification Log (skip-existing does it); an idempotency token; a settings page for the 25 and 5 limits (two constants); a cache on Pending (kept only as a measured fallback); a separate "Who can send" editor (Users screen). I added nothing that is not tied to a drawn feature, except: the optional `reason` on `action_leave`, the `alvoraa_decline_reason` field, the `stalled` counter and the director scope function. Each is justified in the gap table.

## 22 · Definition of Ready check

| Box | Result |
|---|---|
| One named user, one outcome; job in user's words; WOW named | yes (brief) |
| Competitive analysis, Kano marked proxy | yes, but every competitor cell is `[recall — verify]` (brief section 4). **Unticked: unverified claims** |
| Persona enhancements from the UX opportunities scan | **Unticked: `01a-ux-opportunities.md` does not exist in this slice (brief section 9 says so)** |
| Out of scope written; brief approved | yes (brief section 8; 01b D1 to D11) |
| Clickable prototype reviewed by the user | yes (01b "Design approved") |
| Feedback logged in `ux-learnings.md` | `[UNVERIFIED]` I did not check |
| Every state designed: empty, loading, error, no permission, first-time | **Unticked in part: loading and error states are not drawn (02-design section 11, "v1 limit"). Specified in words as AC-65 and AC-73** |
| 01c written with SEC and PRIV | yes |
| 07 sections 1 to 3 with OPS items | yes (07 is one block, dated 27 Oct) |
| Gap analysis against what is actually shipped | yes (section 3) |
| Epic, INVEST stories, sized, linked, "must not" stories | yes |
| Every story has a G/W/T AC with an oracle | yes |
| Traceability complete | yes (section 19), with three gaps named |
| Permission matrix with negative cases | yes (section 7) |
| Edge cases, NFR numbers, migration | yes |
| Compliance sub-analysis; every ⚠ has an owner | yes |
| No prohibited capability | yes |
| Installing an existing Frappe app | not applicable |
| Open questions have owners and none blocks the first day of work | yes; Q1 blocks release, not build |

**Result: three boxes are not ticked (competitor claims unverified, no 01a, loading/error states not drawn).** The rule says more than two means the slice goes back. All three are upstream hygiene, not gaps in this spec, and none changes what gets built. **My recommendation: Surbhi accepts these three in writing and the build starts, or asks for 01a first.** It is her call.

---

## Open decisions for Surbhi (plain words)

1. **Send to more than 200 people at once.** The page cannot finish that inside the tap. It would say "Sending to 238 people. It will show under Notices I sent when it is done." instead of "Sent". That is not in the prototype. Yes or no?
2. **The bell number.** After this, the bell shows unread notices only, the same as the Notices card. Goal and KPI approvals no longer add to it; they are in Pending. Yes?
3. **Leave decline reason.** The sheet asks for a reason. Nothing stores one today. I would store it as a comment on the leave. Where should the employee read it? Not drawn.
4. **An expense with no approver.** If neither the employee nor their department has one, should the portal still accept the claim (my default) or refuse and say "Ask HR to set your approver"?
5. **Opt-out wording** with "on Home" (Q5 default). Yes?
6. **A CXO who is a System Manager** reaches every company. To limit a director to their companies, give them Company permissions and do not make them System Manager. OK?
7. **What counts as a system alert in Notices.** Today only grooming notices are shown in the portal bell. I use those. Other Frappe alerts (assignments, mentions) are not shown. OK?
8. **Release in three parts (A, B, C)** or all at once? Section 20.
9. **The limits 25 and 5 and 300** are fixed numbers in the code, not a setting. A change is a small code change. OK?
10. **"It may have gone through. Check Notices I sent."** when a send times out: add it? (design section 11 asks for your yes).
11. **How is email muted at DTC?** Needed so "email is active" checks the same thing. Owner: Surbhi or DevOps.
12. **Your defaults to confirm:** Q1 (no purge, not live until a number), Q2 (birthdays off until counsel writes), Q4 (only the named approver), Q5, Q6 (no alert when not sent). And the five residual risks in 01c section 12, which are still unaccepted.

## Assumptions

- `[ASSUMPTION]` A1 Everyone has a login (01b D3 update); the audience is Active people with an enabled User.
- `[ASSUMPTION]` A2 "System alerts" in Notices are the grooming notices only.
- `[ASSUMPTION]` A3 The live portal is `portal.js`; the discarded redesign is not used.
- `[ASSUMPTION]` A4 `get_portal_activity` has no caller beyond the four found; the engineer re-greps.
- `[ASSUMPTION]` A5 The limits 25, 5, 300 are constants.
- `[ASSUMPTION]` A6 A joiner of this year is not an anniversary; 29 Feb shows on 28 Feb.
- `[ASSUMPTION]` A7 `waiting_since` for policies has a usable date; otherwise those rows sort last.
- `[ASSUMPTION]` A8 HR Manager can write HR Settings through the doc API. If not, the switch endpoint needs one more counted `ignore_permissions` behind its role check `[UNVERIFIED]`.

## Handoff note (to the engineer and the test engineer)

Read section 7.1 first. The worst bug is a scope check that fails open, and the second is the job running as Administrator. Every scope call in the send job passes `user=<sender>`, and chosen ids are checked with list conditions, never `dict(permitted_employee_filters(), name=...)`. Build the director scope function beside the existing helpers, not inside them. I disagree with one line of 01c: its subtract pass says the leave sheet needs no server code; Decline with a reason needs the optional `reason` on `action_leave`. Make the notice rows type `Alert` or Frappe will email people on any tenant with email on. Do not write the decline reason to `remark`; the claims screen uses it as the title. The expense data-shape matters: PPJ has no claims, so test with a portal-filed claim that has an approver, or the new part proves nothing. Copy exact screen strings from `prototype-v1.html`. Use the 60-cell screen test as the balance oracle, measured on the real cards. The over-200 "Sending" wording, the "on Home" opt-out text and the bell number change are not in the prototype: do not build them until Surbhi says yes.
