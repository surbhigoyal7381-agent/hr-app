# 076 Part B · Security and privacy review (sending and scheduling notices)

Security and privacy engineer · 28 Oct 2026 · ALV-240 · Diff reviewed: `git diff 9c5a5c63..HEAD` on `slice/076-home-notices` (commits `ed0274b3`, `cef77d36`).

**I wrote the requirements in `01c`.** Lesson 6 says I must not be the only person who checks them. The reviewer should check SEC-1 to SEC-6 on their own.

## Verdict: **Fail — two small fixes needed, then Pass**

The scope work is good. The send job always works out the audience as the sender, and the "nobody" rule cannot be overwritten. The two problems are about where the notice text ends up, not about who gets it:

1. **Blocker (P1): if the send job crashes, Frappe writes the notice text and up to 200 recipient email addresses into the Error Log.** SEC-21 not met. About 10 lines to fix.
2. **Major (P1): the raw message can run as a script in a System Manager's Desk session** (print view, or report view with the Message column). SEC-9 only partly met. About 3 lines to fix.

Neither problem has happened anywhere. Part B exists only on the builder's local sites.

## What I ran, and what I could not

- **Ran it:** on Frappe 16.33.1 (`hrlocal-bench`, read-only query on `ppj.localhost`), `[["name","in",[]], ["name","in",["PPJ-0403"]]]` returns nobody, and the control query `[["name","!=",""], ["name","in",["PPJ-0403"]]]` returns `PPJ-0403`. So the list-shaped "nobody" rule really does deny on this Frappe version.
- **Ran it:** Frappe's own `get_traceback(with_context=True)`, the call a failed background job uses, on a throwaway function shaped like `_write_rows`. The output printed `message = '…'`, `users = ['ravi.k@example.com', …]` and `safe = '…'`. No database was touched.
- **Broke a guard in a scratch copy:** I exported HEAD to the scratchpad and removed `esc()` from the card row and from Notices I sent. The DOM test then failed exactly those two checks ("a hostile notice is text on the card", "… in Notices I sent"): 70 passed, 2 failed. The clean copy passes 72 of 72.
- `scripts/check_scope_traps.py` passes on the branch.
- **Could not run:** any Python test. The builder's container `hrlocal-076` is off limits to me, and the shared bench does not mount this worktree. Where I rely on the builder's own break tests (`05-implementation-notes-B.md`, "Each guard was broken on purpose once"), I say so.
- **Could not check:** how email is muted at DTC. That needs read access to the production site config. It is the same gap the builder reported.

## Requirement by requirement

| Req | Status | Mechanism (file:line) | How I checked |
|---|---|---|---|
| SEC-1 role on every endpoint | **Met** | `announcements.py:61-71` `_require_sender` (Guest, role, leaver) is the first line of `notice_reach`, `search_notice_people`, `create_notice`, `cancel_notice` and `my_sent_notices`. `notice_sender_holders` has its own HR check at `:369-373`. The REST door is shut by `announcement.py:26-28` (a request-only flag) | Read the code. The REST insert test is the builder's |
| SEC-2 scope at create and at send | **Met** | `_resolve` `:131-159` works from `_people(sender)` `:87-97` = `notice_audience_conditions(sender)` + Active + `user_id` set + enabled User. A branch or company outside scope gives an empty list, which is refused at `:145-147`. At send it is worked out again (`:462`) | Read the code. A branch-scoped HR person's `["branch","in",…]` drops people with no branch |
| SEC-3 chosen ids never trusted | **Met** | The ids are compared in Python against the in-scope list `:152-158`. Any id outside scope means the whole request is refused, with a count and no names. `access.py:324-355` returns a **list**, and the "nobody" case is `[["name","in",[]]]` | **Ran it** (empty IN denies on Frappe 16, above). No `dict(…, name=)` anywhere in the diff (grep), and the trap script passes |
| SEC-4 job runs as the sender | **Met** | `send_one` uses `sender = doc.owner` (`:457`) for every scope and role call. `notice_audience_conditions(user)` has no default (`access.py:324`). `frappe.session.user` appears only in the endpoints (`:63`, `:369`) | Grep of the diff for `session.user`. The builder's break test ("resolving as Administrator" made 8 tests fail) |
| SEC-5 re-check at send | **Met** | `_sender_problem` `:74-82` (login switched off, role removed, sender has left). Losing scope gives an empty audience, which becomes "Not sent" (`:463-469`). Checked again on resume | Read the code |
| SEC-6 role | **Met** (by the builder's tests) | Patch `notice_sender_role.py` gives the role once and stops if the role exists. `make_role` sets `desk_access 0`. `patches.txt` has no sections, so it runs before the model sync (checked in Frappe's `patch_handler.py`) | Read the code and the Frappe source. The HR-Manager-cannot-grant result is the builder's |
| SEC-7 sent once | **Met** | `get_doc(…, for_update=True)` is the first read in `send_one` `:434`. Status moves Scheduled → Sending, committed `:471-472`. Rows are committed per chunk and existing rows skipped `:479-481`. The job is deduplicated `:384-385`. The 2-minute repeat rule is at `:263-267` | Read the code. See Minor 1 |
| SEC-8 limits on the server | **Met** | 300 characters at `:233` and again in the controller (`announcement.py:34`). The confirm above 25 at `:274`. 5 a day, cancelled ones included (`_sent_today` counts every status), under a User-row lock plus a locking read `:260-269` | Read the code. The parallel test is the builder's. The REST door is shut, so the limits cannot be skipped through it |
| SEC-9 plain text everywhere | **Partly met** | Portal: `esc()` on every sink (`portal.js` `ntRowHtml`, `ntOpenOne`, `ncSentHtml`; `hmOpenSheet` escapes the title). Bell and email: `html.escape` before storage `:406`, `:419`. **Desk: not met.** See Major 1 | **Broke it in a scratch copy** (DOM test failed). Read the Frappe formatter source |
| SEC-10 no change after sending | **Met** | `announcement.json` permissions: Notice Sender read/write/create only on their own; delete for System Manager only. The controller refuses any change except Scheduled → Cancelled (`announcement.py:36-44`). Recipients have no Announcement permission | Read the JSON and the controller |
| SEC-11 cancel only your own, only while scheduled | **Met** | `cancel_notice` `:319-323`: locked read, then an owner check, then a status check. Over REST, Frappe's own-records-only rule stops anyone touching another sender's notice. Changing `owner` fails the write check | Read the code |
| SEC-17 email only when ticked and email is on | **Met** | Rows are type `Alert` (`:408`). In Frappe 16 that type never emails (`hooks.py:82`, `notification_settings.py:83-85`). The tick is refused while email is off (`:254-255`) and checked again at send (`:474`). `email_is_active` uses `frappe.are_emails_muted()` | Read the installed Frappe source. **Ran nothing:** I could not check the mute setting at DTC |
| SEC-18 own notices only | **Met** (Part A, unchanged) | `notices.py`: `for_user` = the caller, plus Frappe's own permission condition | Read the code. Notification Log gives "All" read only, no create, so nobody can fake a "Pinned" row |
| SEC-21 no text, names or emails in logs | **Not met** | The planned logs are clean (`:447-449`, `:497-500`, `refuse` → `log_refusal`). An **unplanned** crash is not. See the Blocker | **Ran it** (traceback with local values) |
| PRIV-1 the warning is advice only | **Met** | The compose text is in place. Spec AC-127 lists it as guidance | Read the code and the spec |
| PRIV-2 Active people with a login, in scope | **Met** | Same as SEC-2 to SEC-5 | — |
| PRIV-3 the audit record | **Met** | Owner, creation, kind and value, the chosen ids, `send_at`, `sent_at`, `reached`, `email_requested`, `email_note`, `status`, `status_reason`. Track Changes is on. Cancel saves with a Version row (`:325`). The recipients are the Notification Log rows | Read the code. See Minor 1 for one way the record can mislead |
| PRIV-4 counts, never names | **Met** | `my_sent_notices` `:342-362` reads two numbers per notice, with a fixed key list. `search_notice_people` gives id and name for in-scope people only | Read the code |
| PRIV-8 holder list is names only | **Met** | `:367-378`: `full_name` only, HR Manager or System Manager only | Read the code |

Parts A and C own SEC-12 to SEC-16, SEC-19, SEC-20 and PRIV-5 to PRIV-7. They are not in this diff.

## Findings, worst first

### Blocker (P1, blocks the release): a crashed send writes the notice text and recipient emails to the Error Log

- **Who, what, and how:** any background run of `send_one` that fails in an unexpected way. Examples: a lock wait that outlasts Frappe's retries, a login deleted between working out the audience and writing its row, or a dropped database connection.
- **Why it happens:** Frappe's job runner catches the failure and calls `frappe.log_error(title=method_name)` (`frappe/utils/background_jobs.py:293,298`). That builds the traceback with `get_traceback(with_context=True)` (`frappe/utils/error.py:68`), which prints every local value in every frame.
- **What gets copied:** in `_write_rows` that means `safe` (the message) and `u` (an email address). In `send_one` it means `users`, `chunk` and `people`, which hold up to 200 logins plus employee names. In `_email` it means `emails`.
- **Where it sits:** the Error Log, kept 14 days on PPJ (Logs To Clear). Every System Manager can read it.
- **Evidence:** demonstrated with Frappe's own function (above). I did not see it end to end on the branch, because I cannot run the branch.
- **The test missed it:** the builder's SEC-21 test (`test_three_stalls_end_in_failed_with_one_clean_error_row`) covers only the planned `log_error(message=…)`. The "login gone" test does not crash, so it proves nothing about this path.
- **Fix:** turn `send_one(name)` into a thin wrapper whose only local value is `name`. It calls the current body inside `try`. On any error it should roll back, log only the notice id and the error class name (not the error text, which can contain an email), and return. The existing stall and resume logic then retries it, and three stalls end in Failed.
- **Test:** force a crash inside `_write_rows`, then check that the Error Log row has no `@` and no message text.
- **Also in the request path:** a 500 error during an in-request send logs the same way (`frappe/app.py:448-449`). That is true of every endpoint in this codebase, so I list it as Worry 1 and do not put it on this slice.

### Major 1 (P1, SEC-9 is Tier 1): stored script in Desk for a System Manager

- **Who, what, and how:** a store's HR person who holds Notice Sender sends `<img src=x onerror=…>`. The `message` field sets `ignore_xss_filter: 1` (`announcement.json`, field `message`), so Frappe stores it raw. The builder did this on purpose (decision 2).
- **Where it runs:** a System Manager later opens the notice's **print view**, or the **report view with the Message column added**. Frappe's Small Text formatting returns the value unescaped. In Python it is `frappe/utils/formatters.py:110-112`, used by `standard_macros.html:174` with no `|e`. In Desk JS it is `formatters.js` Text → Data, lines 257-273 and 45-47.
- **What it means:** the script runs as the System Manager, who can give roles. That is a route from a store HR person up to full admin.
- **Not affected:** the Desk form itself shows a textarea, which is safe. The portal, the bell and email are all safe.
- **Evidence:** inferred from the installed Frappe source plus the JSON. Not demonstrated, because I cannot run the branch.
- **Fix:** remove `ignore_xss_filter`. Store `html.escape(message)`, checking the 300-character limit before escaping. Unescape it in `my_sent_notices`, the way `notices.py` already does for `subject`.
- **Test:** send `<img…>`, then check `Announcement.message` starts with `&lt;img`, and the DOM test still shows the literal text.

### Minor 1 (P3): a repeat within 2 minutes returns the first notice, even when the audience is different

- **Where:** `announcements.py:263-267` matches on sender and text only.
- **What happens:** a sender sends "Stock count at 3 pm" to branch A, then within 2 minutes sends the same text to branch B. They get branch A's notice back, marked `repeat`. Branch B is never told, and the record shows only one audience.
- **Why it matters:** this is the "I was never told" grievance PRIV-3 is meant to answer.
- **Fix:** also match on the audience fields.

### Minor 2 (P4): no cap on the size of the chosen-people list

- **Where:** `_chosen_ids` `:120-128` accepts any length.
- **Effect:** none on scope, because every id must be in scope. The only limit is the web server's request size.
- **Note it:** a cap at the in-scope count (or 1,000) would be one line. Not needed now.

### Worries (not findings)

1. **Every 500 error in the portal writes local values to the Error Log** (Frappe 16 `log_error_snapshot`). For `create_notice` that would include the message and the chosen ids. This is codebase-wide, not caused by this slice. It belongs in the baseline as a shared-control gap (PII in logs). I will raise it separately.
2. A Notice Sender who left but still has a working login can cancel their own scheduled notice through REST. That is harmless (it only stops a send). Noted so nobody is surprised.
3. The email copy sits in Email Queue for 30 days on PPJ, so the message text has one more copy. This falls under Q1.

**Unneeded surface:** none found. No new public route, no cache, no export, no copy of personal data beyond the planned Notification Log rows. One new `ignore_permissions` (`_write_rows`), which is justified. The total count stays at 289.

## What must exist to see each control working (lesson 1)

Two branches in one company, one HR User with a Branch User Permission, one employee with no branch, one director with a Company User Permission and one without, a scheduled notice whose sender then changes, and one recipient with email notifications on. The builder's fixtures have all of these. PPJ has none of the notices, so "0 rows" on PPJ proves nothing.

## The five unaccepted residual risks (01c section 12)

| # | Risk | Accepted? | Does Part B make it worse? |
|---|---|---|---|
| 1 | Personal data in a notice; only a warning stops it | **Not accepted** | **Yes, a little.** The text is copied once per recipient into Notification Log and into Email Queue (30 days). Until the Blocker is fixed, a crash also copies it into the Error Log |
| 2 | No retention number for notices (Q1) | **Not accepted** | As expected, not worse. Nothing is purged: neither Announcement nor Notification Log (no Logs To Clear row on PPJ, checked). It stays a release gate for any live tenant |
| 3 | Birthdays rest on oral advice (Q2) | **Not accepted** | Not touched (Part C) |
| 4 | Permission tests do not run in CI | **Not accepted** | **Yes.** 51 more Tier 1 tests that run only on a local bench. Actions are also failing (ALV-164), so even the static scope-trap check is not running in CI |
| 5 | Anniversary emails ignore the opt-out (Q5) | **Not accepted** | Not touched (Part C) |

**Nobody has accepted any of these.** Each needs Surbhi's name and a date before the push to `dev`. Before the push to `main`, risk 2 needs a counsel number, or a written decision to keep Part B off at DTC.

## Subtract pass

Removed from my draft: a finding that `cancel_notice` locks another sender's row before refusing (no harm, just noise); a finding about the "Send now" 3-second wait (performance, already raised by the builder); a request for a site-wide fix to Frappe's logging of local values (moved to Worry 1, because it is not this slice's change).
