# 076 · Security and privacy requirements

Security and privacy engineer · 27 Oct 2026 · ALV-240 · Built on `01-product-brief.md`, `01b-surbhi-decisions.md` and the approved `02-design.md`.

**Risk tier: 2 overall, with four Tier 1 parts.** Tier 1 means a strong-model build, an independent review and a separate security check at review (`usage-discipline.md` §1). The Tier 1 parts are:

1. Who may send a notice, and to whom (branch and company scope).
2. The scheduled send job (it runs as Administrator, see bad news 1).
3. The manager's expense decision (money: approving books the claim to the ledger, ALV-178).
4. Birthdays and anniversaries (a new use of personal data, read past field rights).

I wrote these requirements. I must not also be the only person who checks them at review (lesson 6). The reviewer must check SEC-1 to SEC-6 and SEC-12 to SEC-16 separately.

---

## Bad news first

1. **The send job runs as Administrator, and the scope helper gives Administrator everybody.** `permitted_employee_filters()` with no `user` returns `ALL_EMPLOYEES` for Administrator (`hrms/hrms/alvoraa_hr_core/access.py:277-278`, verified in code). A scheduled notice resolved with the default user would reach every employee on the site. The job must always pass the sender's user. (SEC-4.)
2. **A notice saved as a normal Notification Log row emails people by itself.** Frappe's `NotificationLog.after_insert` sends an email to each user who has email notifications on, unless the type is in `notification_skip_email_types`, which is only `"Alert"` (`frappe/desk/doctype/notification_log/notification_log.py:61-68`, `frappe/hooks.py:82`, verified in the installed source). On the local PPJ copy 408 users have email notifications on (verified by running a query). So the "email tick" would be a lie on any tenant whose email is not muted. Notices must be written as type `Alert`. (SEC-17.)
3. **Portal-filed expense claims have no approver on them.** `hr_api.apply_expense_claim` builds the claim without `expense_approver` (`alvoraa_portal/alvoraa_portal/hr_api.py:2447-2468`, verified in code). The new expense part reads "claims where I am the approver", so it would show nothing for every manager. The tests would pass and the rule would never fire (lesson 1). Filing must set the approver. (SEC-12.)
4. **Frappe HR's own self-approval check is switched off.** HRMS refuses self-approval only when HR Settings `prevent_self_expense_approval` is on (`hrms/hrms/hr/doctype/expense_claim/expense_claim.py:164-174`). On local PPJ it is `0` (verified by running a query). Leave, attendance fixes and grooming already carry our own `refuse_own_submit` hook; Expense Claim does not (`alvoraa_portal/hooks.py`, verified). (SEC-13.)
5. **The birthday opt-out cannot be honest about email today.** Frappe HR sends work-anniversary emails company-wide when HR Settings `send_work_anniversary_reminders` is on. It is on at local PPJ (verified). Those emails ignore our new opt-out. (PRIV-6, question Q5.)
6. **A non-HR director who holds Notice Sender reaches nobody.** The scope helper gives HR roles and System Manager a scope, and everybody else `NO_EMPLOYEES` (`access.py:276-281`). That is the safe default. It may not be what D8 intends for a CXO who is not HR. (Question Q3.) And today a "CXO" is a System Manager, who gets every company, not "the companies they see".

---

## 1 · Threat model in four lines

1. **Who wants this, and the cheapest way in.** A store's HR person who wants to message another store (edit the request: change the branch, or add people by id). A sender whose role was removed but whose scheduled notice is still waiting. A manager who wants to approve their own claim, or a claim that is not theirs. A curious colleague who wants a co-worker's birth year or exact age.
2. **Blast radius of one mistake.** One tenant, every employee in it: one bad scope check in the send job reaches everyone on the site. Each tenant is a separate site and database, so a notice cannot cross tenants. Cross-company and cross-branch inside a tenant is the real top of the scale here.
3. **What becomes possible that was not.** A person can write to hundreds of colleagues at once. A manager can book money to the ledger from a phone. Birth day and month, and years of service, become visible to colleagues for the first time. A read mark becomes a number HR can see.
4. **How we would find out.** Today: a colleague would tell us. That is the gap. The Announcement record must say who sent what, to which audience, and how many people it reached (PRIV-3), so a complaint can be checked in minutes.

---

## 2 · Data inventory

| Data | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Notice message (300 characters) | internal; may carry personal data despite the warning | tell staff something | **open, counsel (Q1)** | the sender; each recipient sees their own copy |
| Notice audience (kind + company/branch, or chosen employee ids) | internal | send to the right people | with the notice | the sender only; never a recipient |
| Recipient rows (Notification Log `for_user`, `read`) | personal (who got it, whether they opened it) | deliver; give the sender a count | **open, counsel (Q1)**. No purge is configured on PPJ today (no "Logs To Clear" row for Notification Log, verified) | each user their own row; the sender sees **counts only** |
| Sent / read counts | aggregate | show reach | with the notice | the sender |
| Expense claim amount, type, date, note | personal + money | decide the claim | existing claim retention (unchanged) | the claimant, the named approver, HR in scope (existing) |
| Decline reason (140 characters) | personal | tell the claimant why | with the claim | the claimant, the approver, HR in scope |
| Date of birth → day and month only | **sensitive** (field is permission level 2, `employee_field_rights.py:44`) | birthday card | not stored again; computed on read | colleagues in the same company **and** branch, only if the switch is on and the person has not opted out |
| Date of joining → day, month, years of service | sensitive (level 2) | anniversary card | not stored again | same as above |
| Birthday opt-out tick | personal preference | honour the person's choice | life of the Employee record | the person; HR may read it, not change it |
| Org birthday switch | config | on/off per tenant | n/a | HR Manager changes it |
| "Waiting since" date on inbox rows | internal | oldest-first order | not stored | whoever already sees the row |

---

## 3 · Access intent, including who must NOT see what

| Who | May | Must NOT |
|---|---|---|
| Employee | read their own notices; mark their own read; see same-branch birthdays (name, day, years); set their own opt-out | see who else got a notice, who read it, the audience list, any birth year or age, another person's decline reason, another branch's birthdays |
| Notice Sender (HR) | send to Active people inside `permitted_employee_filters(sender)`; see their own notices with counts; cancel their own scheduled notice | reach anyone outside that scope by editing the request; see a per-person read list; edit a sent notice; see or cancel another sender's notice |
| Notice Sender, not HR, not System Manager | nothing until Q3 is answered (fail closed: "No one is in your scope") | — |
| Manager (named expense approver) | see and decide claims where `expense_approver` is them | decide their own claim; decide a claim where they are not the approver; decide one twice |
| HR Manager | flip the birthday switch; see the read-only list of Notice Sender holders (names only) | change a person's opt-out; grant Notice Sender unless they are also System Manager |
| System Manager | grant and remove Notice Sender in Users | — |
| Guest | nothing | call any new or changed endpoint |
| A leaver with a working login | nothing new (every "who am I" here must use `status = "Active"`, lesson 3) | appear in any audience or birthday list; send a scheduled notice after leaving |

---

## 4 · Obligations engaged

All read from `security-compliance-baseline.md`. Its DPDP and CERT-In entries were verified on 24 Aug 2026, 64 days ago, so they are inside the 90-day limit. I did not re-check them for this slice.

| Obligation | Where it bites | Source, date |
|---|---|---|
| DPDP: purpose limitation and minimisation | birthdays are a new use of DOB and joining date; only day, month and years leave the server | baseline §2, 24 Aug 2026 |
| DPDP: notice / consent or legitimate use | showing birthdays to colleagues by default | baseline §2; **counsel agreed orally only** (01b D10) |
| DPDP: storage limitation | notices and read marks need a retention period | baseline §2; counsel's rule "nothing kept for ever" (18 Sep 2026); no number yet for notices |
| DPDP: reasonable security safeguards | scope, escaping, audit | baseline §2 and §5 |
| Self-approval ban (segregation of duties) | expense decision | compliance map F1/B7 |
| CERT-In logs | unchanged by this slice; logs carry ids, never message text | baseline §3, §6 |

**I am not a lawyer.** None of the above is legal advice. The open legal points are in section 8.

---

## 5 · Abuse cases

| # | Actor and act | Stopped by |
|---|---|---|
| A1 | Branch-A HR sends to "branch B" by editing the request | SEC-2 |
| A2 | Branch-A HR adds a branch-B employee id to "chosen people" | SEC-3 |
| A3 | A sender's role is removed, or they leave, after scheduling for Monday | SEC-5 |
| A4 | The scheduler ticks twice, or two workers pick the same notice | SEC-7 |
| A5 | A sender pastes `<img src=x onerror=...>` into a notice | SEC-9 |
| A6 | A sender scripts 50 notices, or skips the "more than 25" confirm | SEC-8 |
| A7 | A manager approves their own expense claim | SEC-13 |
| A8 | A manager approves a colleague's claim by guessing its id | SEC-12 |
| A9 | A curious colleague reads the birthday API response for birth years | PRIV-5 |
| A10 | A person opts out, and still shows up | PRIV-6 |
| A11 | A sender asks "who has not read it?" through the API | PRIV-4 |
| A12 | An employee reads someone else's notification rows | SEC-18 |

---

## 6 · Security requirements (SEC)

Every item says how it is tested. "Test" means a `bench run-tests` test unless it says otherwise. **T1** marks Tier 1.

### Sending notices

**SEC-1 · Only Notice Sender holders may create, send or cancel. T1.**
Every new endpoint refuses Guest (decorator plus an explicit check, the `inbox_api._refuse_guest` pattern) and refuses a caller without the Notice Sender role, on the server. Hiding the button is a courtesy, not the control.
*Test:* call create, send-now and cancel as Guest, as a plain employee and as an HR Manager without the role. Each gets `PermissionError` and no record is written.

**SEC-2 · Scope is enforced on the server, at create and again at send. T1.**
The audience is always the AND of: `permitted_employee_filters(sender)`, `status = "Active"`, a linked and enabled User, and the chosen company or branch. A chosen company must be in `permitted_companies(sender)`; a chosen branch must be in `permitted_branches(sender)` when that is not None. A choice outside scope is refused, not narrowed silently.
*Test:* Branch-A HR (HR User + Branch A User Permission) asks for branch B → refused. Company-X HR asks for company Y → refused. Branch-A HR asks for "everyone" → only branch A people, and nobody with an empty branch (the DEF-6 rule in `permitted_branches`).

**SEC-3 · Chosen people are checked against scope, never trusted from the client. T1.**
The server checks every id in one query. The scope conditions are passed as a **list**, the same way `employee_in_scope` builds them (`access.py:289-299`). If any id is outside scope, inactive, or has no enabled login, the whole request is refused and the reply says how many were refused (no names of out-of-scope people).
**Never write `dict(permitted_employee_filters(), name=X)` or `dict(..., name=["in", ids])`.** Both `NO_EMPLOYEES` and `ALL_EMPLOYEES` are keyed on `name`, so the caller's `name` replaces the refusal and a user with no companies is let in. This is the fail-open trap found in slice 063.
*Test:* (a) a sender with no companies sends to one valid id → refused (this is the test that catches the trap). (b) Branch-A HR sends to one A id plus one B id → refused, nothing written. (c) a leaver's id → refused.

**SEC-4 · The send job resolves scope as the sender, never as itself. T1.**
The scheduled job runs as Administrator. Every scope call inside it passes `user=<sender>` explicitly. No module-level state holds an audience between ticks (one worker serves several sites).
*Test:* schedule a notice as Branch-A HR, run the job function directly (session user Administrator), and assert only branch-A Active people get a row.

**SEC-5 · At send time the sender's right is checked again. T1.**
Before a scheduled notice goes out, the job re-checks: the sender's User is enabled, still holds Notice Sender, and (for HR roles) still has a scope. If any check fails, nothing is sent. The notice is marked "Not sent" with the reason in words. The audience is resolved at this moment, so people who left since are skipped and people who joined are included.
*Test:* four cases, each schedules then changes state, then runs the job: role removed; User disabled; sender's Employee set to Left with no User Permission on Company (so `permitted_companies` falls to nothing); a recipient set to Left. The first three send nothing and record the reason. The fourth skips only that recipient.

**SEC-6 · The "Notice Sender" role. T1.**
Seeded by a patch that is safe to run twice. Given once, at install, to users who hold HR Manager at that moment (Q8), and never again by code. Not desk-access by itself. Not added to any Role Profile or default role. Granting it stays with whoever may edit User roles under Frappe's own rules.
*Test:* run the patch twice → one Role, holders unchanged on the second run. Remove the role from one HR Manager, run the patch again → it is not given back. A user with HR Manager but not System Manager cannot save a User with the role added (`PermissionError`). If that test fails, it is a finding, not a test to relax.

**SEC-7 · A notice is sent once. T1.**
The job reads the notice with `for_update=True` as the **first read in its transaction**, moves it Scheduled → Sending → Sent, and commits per notice. Cancel takes the same lock, so cancel and send cannot both win. (Lesson 5: in slice 021 a plain read before the `FOR UPDATE` re-read gave a stale snapshot.) A second "Send now" from the same sender with the same text within 2 minutes returns the first notice instead of making another (covers a double tap and a retry after a timeout).
*Test:* run the job twice on one due notice → one Notification Log row per recipient. Cancel a notice, then run the job → nothing sent. Call send-now twice with the same text → one notice.

**SEC-8 · The limits are server rules, not form rules.**
300 characters after trimming, not empty. Over 25 resolved recipients needs `confirmed=1` from the client, or the server refuses. At most 5 notices per sender per calendar day (tenant time zone), counted on the server from the sender's notices created that day, **including cancelled and not-sent ones** (so cancel-and-resend cannot get round it). The count check and the insert take a lock on the sender so two parallel requests cannot both be the fifth.
*Test:* 301 characters → refused. 26 recipients without `confirmed` → refused; with it → sent. The 6th notice → refused. Two parallel 5th requests → one succeeds.

**SEC-9 · Message text is plain text everywhere. T1.**
No HTML, no Markdown, no auto-links: a URL is shown as text. The portal renders it with the existing `esc()` helper (`portal.js:215`) in the card, the sheet, See all and Notices I sent. Because the desk bell renders a Notification Log `subject` as HTML, the text is HTML-escaped **before** it is written to `subject` and `email_content`. The email copy is escaped the same way.
*Test:* send `<img src=x onerror=alert(1)>` and `<script>`. Assert the stored `subject` contains `&lt;img`, not `<img`. DOM test (the existing `run_dom_tests.js` runner): each portal surface shows the literal text and creates no `img` or `script` element.

**SEC-10 · A sent notice cannot be changed or deleted by its sender.**
Announcement DocType permissions: Notice Sender may create and read **their own** (if-owner); no write after "Sent"; delete for System Manager only. No read for Employee or any other role. Recipients read only their own Notification Log copy.
*Test:* as a recipient, `frappe.get_list("Announcement")` and `frappe.get_doc` on a notice they received → nothing / `PermissionError`. As the sender, editing a sent notice → refused.

**SEC-11 · Cancel only your own, only while scheduled.**
*Test:* another sender cancels → refused. Cancel a sent notice → refused.

### Expense decision

**SEC-12 · Only the named approver decides a claim. T1.**
The decide endpoint refuses unless the caller is the claim's `expense_approver` and has an **Active** Employee record (lesson 3). Filing in the portal must set `expense_approver` from the Employee record (and the department approver if that is empty, as HRMS does in `hrms/api/__init__.py:612-622`), or the expense part is empty for everyone. Anyone else, including HR, uses Desk until Q4 is answered.
*Test:* file a claim through the portal → `expense_approver` is set. A manager who is not the approver calls decide with the claim id → `PermissionError`, claim unchanged. A leaver who was the approver → refused. **Data-shape check:** on the local copy, count claims with an empty `expense_approver` before and after; the slice must say what must exist for the part to show anything.

**SEC-13 · Nobody decides their own claim, on any door. T1.**
Add `hrms.alvoraa_hr_core.access.refuse_own_submit` to Expense Claim `before_submit`, as Leave Application, Attendance Request and Grooming Mark already have. This does not depend on the HR Settings switch, which is off at PPJ.
*Test:* an employee who is their own expense approver approves through the portal, through `frappe.get_doc(...).submit()` and through REST → refused each time, with HR Settings `prevent_self_expense_approval = 0`.

**SEC-14 · A decision happens once, through Frappe. T1.**
Read the claim with `for_update=True` first; refuse unless `docstatus = 0` and `approval_status = "Draft"`. Approve = set `approval_status = "Approved"` and `doc.submit()`. Decline = set `approval_status = "Rejected"`, store the reason, `doc.submit()`. No raw SQL, no `db_set` on the status, **no `ignore_permissions`**: the approver already has submit rights through the share HRMS adds (`hrms/hr/utils.py:800-808`).
*Test:* approve twice → second call gets "already decided" and no second ledger entry. Approve and decline at once → one wins. A GL entry exists after approval and none after decline.

**SEC-15 · The decline reason is safe and private.**
Required for decline. 1 to 140 characters after trimming. Stored as plain text in one field the claimant's own claims screen already reads (the engineer names the field and checks nothing else writes to it). Rendered with `esc()`. The claimant sees only their own claims' reasons (`get_expense_claims` filters on their own Active Employee, `hr_api.py:2247-2259`).
*Test:* decline with no reason → refused. 141 characters → refused. Reason `<b>x</b>` shows as text. Employee B's claims call never returns employee A's reason.

**SEC-16 · Amounts reach only the approver.**
The new `expense_approvals` part filters on `expense_approver = caller`, `docstatus = 0`, `approval_status = "Draft"`, `employee != caller's own`. It follows every `inbox_api` rule: a non-empty `scope` string, `no_rows()` when the caller has no Active Employee, `get_list` (not `get_all`), the 50-row cap, count equals rows, a `ROW_KEYS` entry. Keys: claim name, employee name, expense type, date, amount, note, waiting-since, action. No bank, no account, no advance.
*Test:* the existing inbox tests (guest, wrong persona, count equals rows, no empty filter) run over the new part. A plain employee and an HR Manager who is not the approver get `count: 0` for it.

### Notification Log, inbox, email

**SEC-17 · No email unless the sender ticked it and email is active. T1.**
Notice rows are Notification Log type `"Alert"`, so Frappe does not email them by itself (bad news 2). The email copy is a separate, explicit send. The tick is accepted only if "email is active for the tenant" (one helper: an enabled outgoing Email Account and email not muted). The job checks the same helper again at send time. If email was muted in between, the notice still goes, the email does not, and the notice records "email not sent: email is off".
*Test:* with mute on, send with `email=1` → refused at create. Schedule with email on, then mute, run the job → notices written, zero Email Queue rows. With a recipient who has email notifications on and no tick → zero Email Queue rows.

**SEC-18 · People read only their own notices.**
The Notices endpoint reads Notification Log through `frappe.get_list` (Frappe's own `for_user` rule, `notification_log.py:104-117`) with a fixed field list. Marking read uses Frappe's own `mark_as_read`, which already filters on `for_user = session user` (`notification_log.py:282-293`). The unread number on the card and on the bell come from **one** function.
*Test:* user B calls mark-read on user A's row → A's row stays unread. The card count equals the bell count for three users with different data. Guest → refused.

**SEC-19 · `get_inbox` changes do not widen anything.**
One new key ("waiting since", a date, no time zone tricks) added deliberately to `ROW_KEYS` for each part. No other key added. No `ignore_permissions`. The 50-row cap stays. Adding the expense part to `parts()` also changes `get_nav_counts`; the total must still equal the sum of parts.
*Test:* the existing `inbox_api` tests pass unchanged; a new test asserts each part's key set is exactly the old set plus the new key.

**SEC-20 · `get_portal_activity` is removed, and nothing else calls it.**
Verified in code: the only callers are `portal.js` lines 5611, 5617, 6223 and 8666, and its own definition at `hr_api.py:1120`. Removing it also removes three `ignore_permissions` calls.
*Test:* `grep -rn get_portal_activity` returns nothing outside `docs/`. A call to the old method returns "not found".

**SEC-21 · Logs carry ids and counts, never message text, names or emails.**
Any error logged by create, send, cancel or decide names the notice or claim id and a count. Not the message, the reason, a recipient's name or email.
*Test:* force a failure in the job (for example a recipient whose User was deleted) and assert the Error Log row has no message text and no email address.

---

## 7 · Privacy requirements (PRIV)

**PRIV-1 · The compose warning is advice, not a control.**
"Do not put pay, health or other personal details in it" stays, as drawn. Nobody may describe it as a safeguard in a spec, a questionnaire or a customer answer. The controls are scope (SEC-2), retention (Q1) and the audit (PRIV-3).
*Test:* review check only. The spec's control table lists the warning under "guidance".

**PRIV-2 · A notice reaches only Active people with a login, inside scope.**
Covered by SEC-2 to SEC-5. Listed here because it is also the minimisation rule.

**PRIV-3 · Who sent what to whom can be rebuilt a year later. T1.**
The Announcement record keeps: sender (owner), created time, audience kind and value (company, branch, or the chosen ids), scheduled time, sent time, number reached, email yes/no, status and reason (sent, cancelled by whom and when, not sent and why). Track Changes is on. The recipients are the Notification Log rows linked to the notice. This is the record that answers a grievance ("I was never told").
*Test:* send one notice, cancel one, have one held. Assert each field is filled and a Version row exists for the cancel.

**PRIV-4 · Read counts are numbers, never names. T1.**
The sender sees "Reached N, read by M". No endpoint returns a per-person read list, including to System Manager through the new code. The count query reads other people's rows, so it returns only two integers.
*Test:* assert the response keys for "Notices I sent" are exactly the agreed list and contain no user, employee or email field.

**PRIV-5 · Birthdays: no year and no age leave the server. T1.**
Date of birth and date of joining are permission level 2 (`employee_field_rights.py:44`), so a plain employee cannot read them through Frappe. The birthday endpoint therefore reads them on the server on purpose. Because it does, it returns a fixed key list only: display name, kind ("birthday" or "anniversary"), day, month, and years of service for anniversaries. No employee id, no date field, no year, no age, no photo.
*Test:* assert the exact key set of every row. Assert no value in the response matches a four-digit year, and no value equals any seeded `date_of_birth` or `date_of_joining`.

**PRIV-6 · The org switch and the personal opt-out are honoured on the server. T1.**
- Switch off: the endpoint returns an empty list and **runs no Employee query** (the `inbox_api` early-return pattern). Switch default at install: **off** on every tenant, so each organisation turns it on deliberately. Only HR Manager (or System Manager) may change it; the change is recorded by Frappe's own history.
- Opt-out: a Custom Field on Employee, read-only in Desk, set only by the person through their own endpoint (no employee argument accepted). HR can read it, not change it. Opted-out people are excluded in the query, not in the browser.
- The opt-out text says what it covers: **Home only**, until Q5 is settled. It must not promise to hide the person from Frappe HR's anniversary emails, which ignore it today.
*Test:* switch off → empty list and zero Employee queries (assert with a query counter). Opt-out person absent from colleagues' lists. A plain employee calling the opt-out endpoint can change only their own record. An HR Manager saving that field on someone else in Desk → refused or ignored.

**PRIV-7 · Birthdays are same company and same branch, Active only.**
The viewer's own **Active** Employee gives the company and branch. A viewer with no branch, or no Active Employee, gets an empty list (fail closed). Leavers, people with no date, and opted-out people are excluded.
*Test:* branch-A viewer never sees branch B or an employee with no branch. A leaver with a working login gets nothing. A person whose status is set to Left disappears from the list.

**PRIV-8 · Notice Sender holder list shows names only.**
The read-only list in Organisation settings is for HR Manager only and returns full names. No email, no user id.
*Test:* plain employee → refused. Response keys are names only.

---

## 8 · Questions for Surbhi or counsel

These are questions, not answers. I am not a lawyer.

| # | Must / should | Question | Blocks | Fail-closed default meanwhile |
|---|---|---|---|---|
| Q1 | **Must** (before go-live at a live tenant) | How long do we keep a notice, its recipient rows and the read marks? Counsel's rule is "not for ever"; there is no number for notices. | Retention setting (Frappe Log Settings for Notification Log is configuration; the Announcement record needs a number too) | Build with no purge; record this as **temporary debt** that a counsel number removes. Do not switch the feature on at a live tenant without it. |
| Q2 | **Must** (before the birthday switch is turned on at a live tenant) | Written confirmation from counsel that showing birthday day/month and years of service to same-branch colleagues, on by default with a per-person opt-out, is allowed, and on which basis (consent or legitimate use). Today it is oral only (01b D10). **Owner: Surbhi.** | Turning the switch on at DTC | Switch ships **off**. Each tenant turns it on only after the written note exists. |
| Q3 | **Must** (blocks D8 for non-HR senders) | A director who holds Notice Sender but is not HR or System Manager: whom may they reach? Their own company? Nobody? And should a CXO be limited to some companies, which today means not making them System Manager? | SEC-2 for that person | They reach nobody, and the Compose screen says "No one is in your scope. Ask HR." |
| Q4 | Should | Besides the named expense approver, may anyone decide a claim in the portal (HR in scope, a stand-in when the approver is away)? | SEC-12 | Only the named approver. Everyone else uses Desk. |
| Q5 | Should | Frappe HR's work-anniversary emails are on at PPJ and ignore the new opt-out. Switch them off on tenants that use the widget (a setting), or keep them and tell staff the opt-out covers Home only? | PRIV-6 wording | Opt-out text says "on Home". |
| Q6 | Nice | When a scheduled notice is not sent (sender lost the right), should anyone be told? | Nothing | Marked "Not sent" with the reason; nobody alerted. |

I decided one thing myself, because it is reversible and affects one sender: cancelled notices count toward the 5 a day (SEC-8).

---

## 9 · CI gate to add

**Verified in code:** CI (`.github/workflows/ci.yml`) runs static checks only. It does not run `bench run-tests`, and there is no `ignore_permissions` counter (compliance map I3, status unknown until now: missing). So the permission tests above are proven on the local bench, not in CI.

One small script, `scripts/check_scope_traps.py`, run in CI:
1. Fails if any Python file contains `dict(permitted_employee_filters(` together with `name=` in the same call, or `{**permitted_employee_filters(`.
2. Fails if the count of `ignore_permissions` in `alvoraa_portal/` and `hrms/hrms/alvoraa_hr_core/` (non-test files) rises above a number stored in the script. Today's count is 289 (verified by running grep). This slice removes 3 (SEC-20), so the slice sets the number to the new, lower count. The number can only go down.

It needs a `--self-test` like the other scripts in `ci.yml`, so it can be shown to fail.

---

## 10 · What must exist for each control to be seen working (lesson 1)

| Control | Needs, on the test data |
|---|---|
| SEC-2, SEC-3 | Two branches in one company, plus one HR User with a Branch User Permission, plus one employee with no branch |
| SEC-5 | A scheduled notice whose sender is then changed |
| SEC-12 to SEC-16 | At least one portal-filed claim with `expense_approver` set. PPJ has **zero** Expense Claims today (verified), so "0 rows" proves nothing there |
| PRIV-5 to PRIV-7 | People in two branches with birthdays and joining days this month, one opted out, one Left |
| SEC-17 | One recipient with email notifications on (408 of PPJ's users are) |

---

## 11 · Worries (not findings)

- Inserting one Notification Log row per person for 1,000 people inside one 3-to-4-minute tick: I have not measured it. DevOps should.
- I did not check whether User role changes are recorded in Version on this site, so I cannot yet say "who gave Notice Sender to whom" can be rebuilt.
- I could not check how email is muted at DTC (production is off limits). SEC-17's helper must be tested against the same mechanism DTC uses; Surbhi or DevOps to confirm which.

---

## 12 · Residual risk

| Risk | Label | Owner | Accepted by, date |
|---|---|---|---|
| A sender puts personal data in a notice; only a warning stops it | intentional trade-off | Surbhi | **accepted by Surbhi, 28 Oct 2026** |
| No retention number for notices (Q1) | temporary debt; a counsel number removes it | Surbhi with counsel | **accepted by Surbhi, 28 Oct 2026** |
| Birthdays rest on oral counsel advice (Q2) | temporary debt; the written note removes it | Surbhi | **accepted by Surbhi, 28 Oct 2026**; switch stays off until then |
| Permission tests do not run in CI | temporary debt; a CI bench job removes it (separate decision) | Surbhi | **accepted by Surbhi, 28 Oct 2026** |
| Anniversary emails ignore the opt-out (Q5) | acceptable simplification if the wording says "Home only" | Surbhi | **accepted by Surbhi, 28 Oct 2026** |

All five were accepted by Surbhi on 28 Oct 2026 (her words: "Accept all 5"). Still to do for her, later: ask counsel for a retention number (risk 2) and a written birthday note (risk 3). Sending stays off at every tenant until a System Manager gives someone the Notice Sender role.

---

## Subtract pass

Removed on this pass: a per-request idempotency token field (the same-text, two-minute rule in SEC-7 does the job with no new field); an alert to HR when a scheduled notice is held (Q6 instead); HR in scope deciding expenses (Q4 instead); a new PII-in-logs scanner (SEC-21's one test is enough for this slice); a DPIA (the new processing is small, same-branch, and opt-out; I would write one only if counsel asks); a separate SEC for the leave Decide sheet (it calls the existing leave endpoints and adds no server code).
