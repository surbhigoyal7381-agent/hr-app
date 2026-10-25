---
slice: 070-readable-on-phone (ALV-217)
artifact: 01c-security-privacy-requirements.md
author: hrms-security-privacy-engineer
date: 2026-10-25
inputs: [01-product-brief.md, 01b-ux-design.md incl. Decisions 25 Oct, 07-devops-inputs.md §1-§2, portal.js, hr_api.py, installed Frappe utils/response.py (hrlocal-213)]
---

# 070 · Security and privacy requirements

**Answer first: no new personal data, no new reader, no new endpoint.** Two real risks: a lost answer turning into a second request, and failure text showing server detail. One existing gap found (W1); it is not this slice's to fix.

## Threat model (four lines)
1. **Who wants what:** the risk is accidental (a double leave, expense or advance), not a thief. The only read is the leave check, which reuses `get_leave_summary`.
2. **Blast radius:** one person's own requests. HR acting for someone stays inside their companies (`_hr_target_employee`, `hr_api.py:2286`). Nothing crosses tenants.
3. **What is new:** a 15 s client time limit, a check before resending a leave, and fixed failure sentences. Nothing new is collected, shown or sent anywhere.
4. **How we would find out:** duplicates show in HR's lists. The tests below catch it before release.

## Data inventory
No new field, DocType, stored copy, export, log or route. Typed form values (a leave reason may be medical) stay in page memory only. **Rung: new code** in `portal.js`. Every cheaper rung was rejected in 01b.

## Abuse and failure cases
- **Lost answer, then Try again:** the server already committed (DevOps §2). Leave: Frappe HR refuses an overlap, and the check runs before any resend. Expense and advance: there is no server guard, so these forms get no Try again (Decision D2).
- **Reading someone else's leave through the check:** the check calls the existing `get_leave_summary`. A non-HR caller passing `employee_id` gets their own record back (**Verified in code**, `hr_api.py:2310-2313`). Adding a new argument would open a new hole.
- **Server detail in error text:** `gpErr` (`portal.js:8930-8931`) shows the last line of `r.exc` (the traceback, meaning the server's internal error report) when there is no message. Frappe sends `exc` to system users, which includes HR and managers, when `allow_error_traceback` is on (**Verified in code**, installed `frappe/utils/response.py:68-78, 195-198`). That line can name tables, SQL errors or document IDs.
- **Raw Frappe messages with IDs:** validation messages (for example the overlap message, which names the employee ID and the Leave Application) stay as they are today (brief item 3). They describe only the caller's own record, or one HR may already act for. **Inference:** this shows nobody anything new.
- **A shared phone:** a draft saved in browser storage would show the next user a medical leave reason. Offline drafts are out of scope (UXB-12).

## Requirements
| ID | What must be true | How it is tested |
|---|---|---|
| SEC-1 | A lost answer never creates a second Leave Application. Submit and Try again are disabled while Sending… or Checking… is showing. | Browser test: the server saves, the answer is dropped, Try again is tapped → exactly 1 record. A double tap → 1 record. |
| SEC-2 | After a lost answer, the expense claim and advance forms show "Look in your list…" with **Close** and no resend control. Nothing retries by itself, anywhere (OPS-4). | Browser test: the server saves, the answer is dropped → no button sends again; the server shows 1 Expense Claim / 1 advance. Grep: no timer calls `api()` again after a failure. |
| SEC-3 | The leave check reuses `get_leave_summary` unchanged: no new endpoint and no new argument. The `employee_id` sent is the same one passed to `apply_leave`, and only on the HR on-behalf path. | Diff review: no new `@frappe.whitelist`. The existing test still passes: a non-HR caller with someone else's `employee_id` gets only their own rows. |
| SEC-4 | Failure text never comes from `r.exc`, a traceback or the HTTP status text. It is either a fixed sentence from 01b §6 or a `_server_messages` message, unchanged. This applies to `gpErr` and to the new helper. | Unit/browser test: a forced 500 with `exc` set as a System User → only "Something went wrong at the office." appears; the DOM (the page's built content) has no traceback text. A forced 417 `frappe.throw` → that message, unchanged. |
| SEC-5 | Validation and permission refusals still show and still block. The 15 s path never treats a refusal as "may have gone through", and never resends after one. | Browser test: an overlap and a refused `on_behalf_of` each show the server message, with no Try again loop and no record created. |
| PRIV-1 | Typed values are kept in page memory only. Nothing goes into `localStorage`, `sessionStorage`, IndexedDB or the URL. | Grep the diff for those APIs (0 new hits). Browser test: reload after a failure → the form is empty. |
| PRIV-2 | No new `console.*` call or error log contains form values or response bodies. | Grep the diff; the PII-in-logs scanner passes. |

**Obligations engaged:** none new. This is DPDP reasonable security safeguards in general (baseline verified 24 Aug 2026, 62 days ago, still within 90 days). Nothing here depends on a point of law.

## Worries (not findings)
- **W1, existing, outside 070:** `get_leave_summary` checks HR scope by **company** only. `apply_leave` also checks **branch** (`_leave_subject`, `permitted_employee_filters`). So an HR user limited to some branches might read the leave of a same-company employee in another branch, through the Team View path (`portal.js:5253`). Lesson 2 pattern. I could not check whether any tenant has HR users limited by branch. Suggest a YouTrack ticket. The default if a fix is wanted: apply the same branch filter there.
- Does `frappe.call` show its own error pop-up (with traceback for system users) next to ours? Open question in 01b for the engineer. SEC-4's test covers it.

## Questions
None must-know. The single should-know (W1) does not block 070.

**Subtract pass:** removed a request-key requirement for expenses (D2 already removes the resend), a cache rule (DevOps OPS-3 covers it), and an audit-entry requirement (nothing new is decided or changed).
