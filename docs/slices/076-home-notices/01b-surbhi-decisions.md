# 076 · Surbhi's decisions, 27 Oct 2026

On the product brief (`01-product-brief.md`), decisions D1 to D11. ALV-240.

| # | Decision |
|---|---|
| D1 | Pending is built on the existing inbox. Approve and decline stay on the existing screens. (Recommendation accepted.) |
| D2 | Confirm above 25 people. 5 announcements a day per sender. (Accepted.) |
| D3 | Staff with no login: not in this slice. (Accepted. The count of DTC staff with a login is still unknown.) |
| D4 | Email copy of an announcement: only when email is active for the tenant. Not before. At DTC email is still muted, so no email goes. |
| D5 | **Yes: DTC managers approve expenses, and they belong in the manager's Pending list.** This changes the brief's recommendation. The portal has no manager expense approval screen, so the design must say how a manager approves an expense from Pending, using the smallest path (reuse first). |
| D6 | Show "Nothing waiting" cards instead of hiding empty ones. (Accepted.) |
| D7 | Notices in English only. (Accepted.) |
| D8 | Management who may send: the CXO users she names, through a named role, each limited to the companies they see. Line managers do not send. (Accepted.) |
| D9 | One Notices card (announcements pinned, system notifications below). (Accepted.) |
| D10 | Birthdays and anniversaries: branch only, name and day and years of service, no age, a per-person opt-out. Birthdays off until counsel agrees; anniversaries on. (Accepted.) |
| D11 | Empty cards show a short "nothing" card. (Accepted.) |

Also from her: the Activity widget goes; the Home page must be balanced in length and breadth.

## Updates, 27 Oct 2026 (later the same day)

| # | Update |
|---|---|
| D3 | All staff will have logins. Notices reach everyone. The worry about staff with no login is closed. |
| D8 | Yes, but NOT hard-coded. "Management" is mostly the top two levels. It must be a setting the organisation can change, not a name or role fixed in code. How the top two levels are found (reporting chain, grade, or a named list) is open: the business analyst must settle it with her. |
| D9 | One Notices card. |
| D10 | Counsel agrees (said orally to her, not in writing). Birthdays are allowed. Each organisation can switch the birthdays and anniversaries widget on or off in a setting. The per-person opt-out stays unless she says otherwise. |
| D11 | Yes: empty cards show a short "nothing" card. |

## D8 simplified (27 Oct 2026)

Whoever has access to announcements can make announcements. Access is a permission the organisation gives to chosen people (a role on their login), not a rule worked out from the reporting chain or grade. This settles the open question about the "top two levels": nobody has to compute it. The organisation gives the access to whoever it wants, mostly the top two levels and HR. Each sender can still reach only the people inside their own company and branch scope.

## Design approved, 27 Oct 2026

She reviewed prototype v1 (Artifact "Home Page Prototype"): "prototype looks beautiful. I wish to get this design exactly this way." Yes to all eight design questions (02-design.md section 13):
Q1 empty card may stretch; Q2 Today strip inside check-in; Q3 leave Approve/Decline in the sheet; Q4 cancel a scheduled notice (yes); Q5 full names in birthdays; Q6 Pending oldest first (one new inbox key); Q7 decline reason shown to the employee; Q8 HR Managers get Notice Sender at install, then the organisation owns it.
Prototype parity applies: build every drawn feature exactly as drawn (02-design.md section 14). Row 30 (cancel a scheduled notice) is now in.

## Security questions, 27 Oct 2026 (01c section 8)

- **Q3: B.** A director with the Notice Sender access reaches only the companies they look after (their company User Permissions), not the whole organisation. Compose shows only those people.
- **Q1, Q2, Q4, Q5, Q6:** she gave no separate answer. The spec uses the security engineer's recommendations as working defaults, and says so, for her to change when she reads the spec: Q1 no deletion yet, feature not switched on at a live tenant until counsel gives a number; Q2 birthdays switch ships OFF until counsel confirms in writing; Q4 only the named approver decides an expense in the portal; Q5 opt-out text says "on Home"; Q6 a notice not sent is marked "Not sent" with the reason, nobody alerted.

## Spec decisions, 27 Oct 2026 ("yes to all")

She answered "yes to all" to the twelve decisions at the end of 03-functional-spec.md. Where a question was either/or, the analyst's and my recommendation is taken:
1. A notice to more than 200 people runs in the background; the page says "Sending to N people. It will show under Notices I sent when it is done."
2. The bell shows unread notices only; goal and KPI approvals move to Pending.
3. A leave decline reason is stored as a comment on the leave; the employee reads it on their own leave request row (the spec's recommendation).
4. An expense claim with no approver is REFUSED with "Ask HR to set your approver."
5. Opt-out wording says "on Home".
6. A director is limited to their companies through company permissions; do not make them System Manager.
7. Alerts in Notices are grooming notices only for now.
8. Release in THREE PARTS: A (Home only), then B (sending), then C (expenses and birthdays). Each push to dev and to main waits for her own word.
9. The limits 25, 5 and 300 are fixed in code.
10. A send that times out shows "It may have gone through. Check Notices I sent."
11. How email is muted at DTC is to be read by the engineer and DevOps from the site, read-only; she is the owner of any change.
12. The working defaults for Q1, Q2, Q4, Q5, Q6 stand.
