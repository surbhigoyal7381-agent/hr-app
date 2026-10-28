---
slice: 076-home-notices
artifact: 06-review-B (senior architect review, change-process step 5, Part B only)
author: hrms-technofunctional-reviewer
date: 2026-10-28
branch: slice/076-home-notices. Part B is ed0274b3 (code) and cef77d36 (notes) on origin/dev 9c5a5c63. I fetched origin/dev again today and it has not moved. Nothing is pushed.
---

# 076 Part B review: sending and scheduling notices

## Verdict: BLOCK. One small fix stands between this and SHIP WITH FIXES.

**A notice can quietly fail to reach a whole branch, and the page then tells the sender it was sent.** This comes from the "same text within 2 minutes" rule. I proved it by running the code (Blocker 1). The fix is a few lines, but it narrows AC-18 as written, so Surbhi or the analyst has to agree to it.

Everything else is in good shape:

- **No leak and no widening was found.** The send job works out who to reach **as the sender**, even though it runs as Administrator.
- **The server refuses** anyone without the role, anyone outside the sender's scope, a 6th notice in a day, and more than 25 people without a confirm.
- **Rows are type "Alert"**, so Frappe sends no email by itself.

Two P2 items need Surbhi's decision before release: the 3-second "Send now", and the Q1 release gate, which has no mechanism behind it.

`BLOCK` and `SHIP WITH FIXES` are advice. Neither is permission to push.

**What I ran.** I started the engineer's stopped `hrlocal-076` containers, ran tests on the engineer's own site `test076`, and stopped the containers again.

| Run | Result |
|---|---|
| `test_announcements_076` | 51 run, OK |
| `test_notices_076` | 9 run, OK |
| `test_portal_security_010` | 45 OK, then 5 OK (two batches) |
| DOM suite | 18 files run, 0 failed; the new file passed 72 of 72 |
| `check_scope_traps.py`, `check_app_integrity.py` (854 checks), `check_brand_spelling.py` | all OK |
| One probe script, run on `test076` | results below; it deleted every record it made |

I also broke a scratch copy for the scope-trap check (see P4).

**Not run:** the whole app suite, a real browser, and any timing measurement. Every time in this review comes from the builder's notes and is labelled that way.

---

## Blocker (P1)

### 1. The "same text within 2 minutes" rule swallows a real second notice, and the page says "Sent"

- **Where:** `announcements.py:263-267` decides what counts as a repeat. `portal.js` `ncDone` writes the message the sender sees.
- **What the code does.** Any notice from the same sender with the same text in the last 2 minutes counts as "the first one". It ignores the audience and the status. The reply is the old notice, with `repeat: 1`. The page never reads `repeat`.
- **Proven by running it on `test076`:**
  - **Different branch.** Company-X HR sends "Office shut tomorrow" to Branch A, then the same text to Branch B. The second call returns the first notice: `status: Sent, people: 3, repeat: 1`. Bina, who is in Branch B, got **0 rows**. The page would show "Sent to 3 people. They will see it on Home and in the bell."
  - **Cancelled first.** The sender schedules "Training at 3", cancels it, then sends the same text now. The reply is the **Cancelled** notice (`status: Cancelled, people: 0, repeat: 1`). Nothing is sent. The page shows "Sending to 0 people. It will show under Notices I sent when it is done."
- **Why it matters.** HR with two branches will often send one line to each branch, one after the other. Cancelling and resending at the right time is exactly what the cancel button exists for. In both cases a group misses an office notice, and the sender is told it went out. That is ranked 3 in the priority order (the business asked for correct delivery). In a first week at a client, it looks like the product lies.
- **The code follows the spec.** AC-18 says "same sender, same text, within 2 minutes returns the first notice". So the rule itself is too broad, not the build.
- **Smallest fix (about 5 lines plus one test):**
  - Count a notice as a repeat only when the text **and** the audience match: kind, company, branch and the chosen ids.
  - Never treat a notice that is `Cancelled` or `Not sent` as a repeat.
  - When `repeat` is 1, the page says "You sent this a moment ago. It is listed under Notices I sent." instead of "Sent to N".
  - Add one test for each of the two cases above.
- **Escalation.** *Decision needed:* narrow AC-18 as above. *Owner:* `hrms-business-analyst` to reword the AC, then Surbhi, then `hrms-fullstack-engineer`. *Risk if it waits:* any tenant that gets Part B. *My recommendation:* narrow it. A double tap is still caught, because it has the same audience.

## Majors (P2: each needs a fix or Surbhi's written acceptance)

### 2. "Send now" to up to 200 people holds the page about 3 seconds

- **Builder's measurement; I did not re-measure it.** It takes about 15 ms per person (980 people took 14.4 s). That makes 200 people about 3 s inside one request.
- **What the budget says.** `nfr-budget.md`: an API call should take ≤ 500 ms (line 57). Work over 2 s goes to the background (line 68).
- **The impact analysis did not see this coming.** `04-impact-and-strategy.md` row "Performance" says the send runs "in a background job". In the code, 200 people or fewer are written inside the request (`announcements.py:295-297`). The builder reports this honestly as bad news 1.
- **What happens.** The button is switched off and the page waits. Nothing breaks: the page gives up after 15 s, and 3 s is well under that. But it also keeps one web worker busy for 3 s. At the end of a month, a few HR people sending at once slow down everyone else's pages on that tenant. **[Inferred]**: I have not counted DTC's workers.
- **Smallest fix.** Set `SEND_IN_REQUEST = 25`, the same as the confirm threshold. That is about 0.4 s by the builder's rate. Anything bigger already has an approved message: "Sending to N people…".
- **This is Surbhi's call.** Her decision 1 covered only "more than 200". People who send to 26–200 would now see "Sending" instead of "Sent". **Recommend: 25.**

### 3. The Q1 release gate ("not at a live tenant until counsel gives a retention number") has nothing in the code behind it

- **Proven by reading.** The code has no per-tenant switch, and none was asked for. On the next `bench migrate`, `patches/v1_0/notice_sender_role.py` gives Notice Sender to every enabled HR Manager on **every** site. That includes `dtc.alvoraa.co`. From then on "Send a notice" appears at DTC.
- **So the only gate is "do not release Part B to main".** Once Part B is on `dev`, every later dev-to-main release carries it. That includes Part C and any other slice that lands after it.
- **Options for Surbhi:**
  - **(a) Keep Part B local** (it is unpushed today) until counsel gives the number. Part A and other work keep moving. **This is my recommendation.**
  - (b) The patch makes the role but gives it to nobody. Each organisation then gives it in Users, so DTC stays off until someone ticks it. This reverses design Q8.
  - (c) Accept in writing that `main` is held while Part B is on `dev`.
- **Owner:** Surbhi, with `hrms-devops-engineer` for the release order.

## Minors (P3: can ship if written down with an owner)

### 4. A notice in Frappe's desk bell links to a page the reader cannot open

- **Proven by reading Frappe.** The desk bell links any row with no `link` to its document (`frappe/public/js/frappe/ui/notifications/notifications.js:388-398`). That opens `/app/announcement/ANN-…`. A recipient has no permission on Announcement (by design, AC-41), so HR Managers, managers and CXOs who use the desk get "Not permitted".
- **Fix.** Set `link` on each row in `_write_rows` to the portal Home. One field.

### 5. Parity row 31 (the holders list) differs from the drawing

- **What differs.** The prototype shows a job title under each name, and "Last changed by Kavita Rao, 20 Oct 2026" **inside the holders card** (`prototype-v1.html:427-428`). The build shows names only and no "Last changed" line.
- **The builder's reading.** They place "Last changed" with the birthdays switch, from design §7. That reading is arguable: the drawing she approved puts it in the holders card.
- **On the job title, PRIV-8 says "names only".** But every recipient already sees the sender's job title in the notice itself (`sender_label`, for example "Hra N076, Store HR N076"). So showing it to HR exposes nothing new.
- **My recommendation.** Add the job title, which is a parity fix. Ask her about "Last changed": it would mean reading role changes from the User history. **Under the parity rule she must say yes either way.**

### 6. Parity: branch names for a CXO lack "(company)"

- The prototype draws "Noida unit (Alvora Retail)" for the CXO (`prototype-v1.html:239`). The build shows the branch name alone (`_targets`, `announcements.py:116`).
- Where two companies use similar branch names, the CXO cannot tell them apart. Small fix, or her yes.

### 7. The patch may remove the Employee role from some HR Manager logins

- **Inferred.** `add_roles` saves the User. ERPNext's `validate_employee_role` (`erpnext/setup/doctype/employee/employee.py:349-363`) then removes "Employee" and "Employee Self Service" from any login that has no linked Employee.
- **Who is hit:** an HR Manager login that is not a staff member (a consultant account, for example) loses those two roles at migrate.
- **Impact is small, but it is a change to live users.** Say so in the release note. **Not checked:** how many such logins DTC has.

## P4 (backlog)

- **The scope-trap check still misses two indirect forms.** I re-proved it in a scratch copy: `f = permitted_employee_filters(u); f["name"] = x` and `f.update(name=x)` both pass. The self-test passes and the plain `dict(…, name=x)` form is caught. Part B does not depend on this check: its list-shaped helper cannot have this trap. The gap is carried over from the Part A review.

---

## The things I was asked to check hard

| # | Question | Answer | Label |
|---|---|---|---|
| 1 | Can the send job reach beyond the sender's scope? | **No.** Every scope call names the sender: `_people(sender)` → `notice_audience_conditions(user)` → `permitted_employee_filters(user)` / `permitted_companies(user)` / `permitted_branches(user)` / `get_user_permissions(user)`. None of them falls back to the session user when `user` is given. The helper returns a **list**, so `["name","in",ids]` can only narrow. There is no `dict(…, name=X)` anywhere. A director gets their Company permissions only, with no fallback (`access.py:345-355`). `test_job_resolves_scope_as_the_sender` runs as Administrator and checks the exact set of people. It passed. | Proven (code and test run) |
| 2 | Does the server refuse out-of-scope, non-sender, over-limit, and over-25 without confirm? | **Yes.** `_require_sender` covers all five endpoints. An out-of-scope id, branch or company is refused at create. The limit is 5 a day, counting cancelled ones. Two requests at once on two connections give exactly one success, because the sender's User row is locked. I also tried moving a notice's `creation` back a day through the REST update path to dodge the daily count: Frappe refused all 5 with `CannotChangeConstantError`. **But the 2-minute rule is wrong** (Blocker 1). | Proven (probe and tests) |
| 3 | Type "Alert", no Frappe email, email only when active? | **Yes.** In Frappe `hooks.py:82`, `notification_skip_email_types = ["Alert"]`, and `is_email_notifications_enabled_for_type` returns False for it. `email_is_active()` is checked at create and again at send. AC-54, 55 and 56 tests passed. **Not checked:** DTC's live `mute_emails`. | Proven / Not checked |
| 4 | Who can cancel whose? | The owner cancels their own notice, only while it is Scheduled. The endpoint locks the row first (`cancel_notice`). A REST edit by the owner can only change Scheduled to Cancelled (controller), and Frappe's `update_doc` also locks the row. System Manager can delete. Another sender, an HR Manager or a leaver cannot. | Proven (code and tests) |
| 5 | "Send while the page waits", up to 200 people, against the 500 ms budget | Misses the budget by about 6 times (Major 2). | Builder's number; inferred |
| 6 | Prototype parity | Rows 12–30 and 33 match, as far as I read them against `prototype-v1.html:360-400`. Row 31 differs (Minor 5), and the CXO branch label differs (Minor 6). "A branch or company" is left out when the sender has no branch or company to choose. That is sensible, but it is not drawn. | Proven by reading; no browser |
| 7 | en.csv and subscription.py | The new DocType is named `Announcement`, with no "Alvoraa" in it, so no en.csv row is needed. The brand check passes. It is listed in `TENANT_DOCTYPES` (`subscription.py:612`). No clash with any DocType in frappe, erpnext, hrms or india_compliance (I searched the image). | Proven |
| 8 | Personal data in logs, payloads or the feed | The send log carries the id, outcome, count and seconds. The Error Log carries the id and counts (test passed). Refusals log the user id only (existing pattern). `my_sent_notices` gives counts, never names. Search gives id and name, in scope only. The feed shows the sender's name and job title, as designed. Email recipients are not shown to each other: Frappe sends one copy per person unless `expose_recipients="header"`. | Proven |
| 9 | Anything from Part C leaking in | **None.** No birthday, anniversary or expense code is in the diff. | Proven (grep of the diff) |

## Acceptance criteria (Part B)

| AC | Status | Evidence |
|---|---|---|
| 1, 2, 4 | met | `test_the_role_is_given_once_and_never_again`, `…no_profile…`. Passed. |
| 3 | met | `test_an_hr_manager_cannot_give_the_role`. Passed. |
| 5–13 | met | `TestScope`, 9 tests. Passed. |
| 14 | met | All five endpoints, three kinds of caller. Passed. |
| 15–17, 19–22 | met | `TestLimits`. Passed, including the two-connection race. |
| **18** | **met as written; the rule is wrong** | Blocker 1. Probe output above. |
| 23–35 | met | `TestSend`. Passed. |
| 36–38 | met | `TestCancel`. AC-38 is tested one order after the other; the row lock covers true overlap. **[Inferred]** |
| 39–43 | met | `TestNoticesISent`. Passed. |
| 44–52 | met | DOM file, 72 of 72. |
| **50** | **partly** | The "Sent to N" line is wrong when `repeat=1` (Blocker 1). |
| 53–56 | met | `TestEmail`. Passed. |
| 57, 58, 62, 63 | met | `TestRecipientFeed`, plus `test_notices_076` (9, OK). |
| 64 | met (builder) | Builder's EXPLAIN on 100,000 rows. Not re-run. |
| 107 | met as specified; differs from the drawing | Minor 5. |
| 117, 118 | met | Scope check OK. Ceilings in `test_portal_security_010`: `announcements.py` 1, the others 0. Passed. |
| 125 | partly | Measured with 980 people, not 1,200 (builder). |
| 122–124, 126, 127 | not this step | Release checks. |

## NFRs, and the seven dimensions against the impact analysis

| Dimension | Impact analysis said | What the code does | Finding |
|---|---|---|---|
| Performance | Home neutral; the send in a background job | Home: the feed stays at 2–3 queries (builder). **The send is in the request for 200 people or fewer, about 3 s.** | **Worse than claimed**: Major 2 |
| Security | New reach, held by scope as the sender | Held. One `ignore_permissions`, which is counted. The REST door is shut. Changing `creation` is refused by Frappe. | Matches |
| Reliability | Locks, chunks, resume, Failed after 3 | As claimed. Resume and kill tests passed. | Matches |
| Scalability | One row per person; no purge | As claimed. `_people` reads the whole scope into memory on each Compose open: fine at DTC's size. **[Inferred]** | Matches |
| Maintainability | One DocType, one module | As claimed. Clear comments. | Matches |
| Data integrity | A notice goes once | Yes for the same notice. **But one intended notice can be dropped as a "repeat"** (Blocker 1). | **Worse than claimed** |
| Compliance / privacy | Counts not names; Q1 is a gate | Counts not names: yes. **The Q1 gate has no mechanism** (Major 3). | **Partly** |

## Compliance

| Obligation | What in the diff makes it true | Test | Status |
|---|---|---|---|
| SEC-1 role on every endpoint | `_require_sender` | `test_without_the_role_every_endpoint_refuses` | discharged |
| SEC-2, 3 scope at create | `_resolve`, list conditions | `TestScope` | discharged |
| SEC-4 job runs as the sender | `user=sender` throughout | `test_job_resolves_scope_as_the_sender` | discharged |
| SEC-5 sender checked again at send | `_sender_problem` | `test_the_sender_is_checked_again_at_send_time` | discharged |
| SEC-7 once only | row lock, skip existing rows, dedupe job id | resume, twice-run and race tests | discharged for one notice; **the repeat rule is too broad** (Blocker 1) |
| SEC-9 escaping | stored as typed; escaped in subject, email and page | `test_html_is_stored_escaped…`, DOM | discharged |
| SEC-11 owner-only cancel | `cancel_notice`, controller | `TestCancel` | discharged |
| SEC-17 no email unless ticked and active | type Alert, `email_is_active` | `TestEmail` | discharged |
| SEC-21 no text in logs | `_log`, `log_error` | `test_three_stalls…` | discharged |
| PRIV-3 who sent what, who cancelled | fields, plus a Version row on cancel | `test_the_record_answers…`, `test_cancel_leaves_a_version…` | discharged |
| PRIV-4 counts, never names | `my_sent_notices` | `test_counts_only…` | discharged |
| PRIV-8 holders: names only | `notice_sender_holders` | `test_the_holder_list…` | discharged (parity question in Minor 5) |
| Q1 not at a live tenant until a retention number | **nothing in the code** | none | **not discharged**: Major 3 |

## What to delete

Nothing has to go. Every extra I looked for traces to an approved item:

- the `stalled` counter (OPS-9)
- the `after_install` line (otherwise a new tenant's senders become desk users)
- the REST guard (otherwise the limits only exist on the page)
- `sender_label` (frozen by spec)

One optional deletion, if Surbhi chooses it under Major 2: send **everything** through the background job and remove the in-request branch (`announcements.py:295-299`). That is simpler code, but every "Now" would show "Sending" instead of "Sent".

## What was done well

- **Scope as a list, with no default user.** `notice_audience_conditions(user)` has no default `user` and returns a list. Both the "Administrator reaches everyone" trap and the `dict(…, name=X)` trap are impossible by shape, not by care.
- **Each guard was broken on purpose to prove its test can fail.** The notes list the counts. That is the answer to "check that the tests test what they claim".
- **The REST door was shut.** The builder noticed that giving the role "create" would let `POST /api/resource/Announcement` skip every limit, and closed it in the controller, with a test.
- **The `after_install` catch.** Frappe would have created the role with desk access on new tenants. That trap is easy to miss.
- **Honest notes.** The 3 s send, the 980-instead-of-1,200 measurement and the parity difference were all reported up front, as bad news.

## Confidence

- **Proven:**
  - scope, refusals, limits, cancel and email behaviour (code read, plus 51 + 9 + 50 tests run by me)
  - the Blocker (probe run on `test076`)
  - Frappe's Alert, `creation` and desk-link behaviour (read in the image `dev-3830ed3`)
- **Builder's numbers, not re-measured:** every timing, query count and EXPLAIN.
- **Not checked:**
  - a real browser
  - DTC's `mute_emails`, worker count, and HR Manager logins without an Employee record (all need read-only server access)
  - the full app suite
- **Subtract pass on this review.** I removed three findings I could not prove:
  - a guess that `owner` could be changed through REST (Frappe's if-owner write check stops it)
  - a guess that `creation` could be changed (the probe showed Frappe refuses it)
  - a timezone worry on "Send later" (server and browser are both IST at DTC; nothing showed it breaking)
