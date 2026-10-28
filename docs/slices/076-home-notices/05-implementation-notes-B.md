---
slice: 076-home-notices
artifact: 05-implementation-notes-B (Part B, sending and scheduling notices)
author: hrms-fullstack-engineer
date: 2026-10-28
status: built and tested LOCALLY on branch slice/076-home-notices, in my own container hrlocal-076 on my own sites test076 and test076l. Not pushed. No server, shared bench, dev or production site touched.
tier: 1 (scope, the send job, email). Plan: 04-impact-and-strategy.md, Part B.
---

# 076 Part B: sending a notice. Implementation notes

## Fix pass after the reviews (06-security-B.md, 06-review-B.md), 28 Oct 2026

Surbhi's decisions: (a) "Send now" waits for at most 25 people; (b) the sender list is built as the prototype draws it. Local only, not pushed. **Not done on purpose:** the "same text within 2 minutes" rule (AC-18, review Blocker 1) is unchanged, waiting for her answer through the coordinator.

| # | Finding | What I did | Proof |
|---|---|---|---|
| 1 | SEC-21 (security Blocker): a crashed send would have put the notice text and up to 200 emails in the Error Log | `send_one(name)` is now a thin wrapper whose only local value is the id. On any error it rolls back, logs `"<id>: <ErrorClass>"` and nothing else, and returns. The notice stays as it was, so the scheduler resumes it, and three stalls end in Failed. `create_notice` commits the notice before an in-request send, so a crash cannot lose it | New test `test_a_crashed_send_logs_only_the_id_and_the_error_type`: the error even carries an email in its own text; the Error Log row is exactly `ANN-…: ValueError`. Broken on purpose (wrapper removed): 2 tests failed |
| 2 | SEC-9 (security Major): the raw message could run as script in a System Manager's desk print or report view | The message is stored HTML-escaped. The "skip Frappe's cleaner" flag is gone and the field is required again. The 300 limit counts what was typed. `my_sent_notices` and the feed unescape for the page, which escapes again. The rows and the email use the stored, escaped text | New test `test_a_script_is_text_everywhere_the_notice_goes`: `<script>` stored as `&lt;script…`, literal in the card, the bell and Notices I sent, not code in `frappe.get_print` or a formatted report cell. Plus `test_300_typed_characters_…`. Broken on purpose (store raw): 4 tests failed |
| 3 | Q1 retention gate had nothing behind it (review Major 3) | **I chose: the role is the switch, and it ships with nobody holding it.** The patch now only makes the role (no desk access) and gives it to nobody, on every site. Sending stays off at DTC and everywhere until a System Manager ticks the role on someone in Users, which Frappe records in the User's history. No new setting was needed. This replaces Q8 ("HR Managers get it at install") until counsel gives a number. Because the patch saves no User, it can never strip the Employee role from an HR Manager login with no Employee record (review Minor 7) | `test_the_patch_makes_the_role_and_gives_it_to_nobody` (an HR Manager login with no Employee record keeps every role, and is not even saved). Spec AC-1/AC-2 annotated |
| 4a | Desk bell sent readers to a record they may not open | Each row's `link` is `/hrms-employee`. The portal feed still shows no link for announcements (it opens the notice itself) | Asserted in the script test |
| 4b | CXO branch list without company | A sender who sees more than one company gets "Noida unit (Alvora Retail)"; one company stays "Noida unit" | `test_a_cxo_sees_each_branch_with_its_company` |
| (a) | Send now holds the page | `SEND_IN_REQUEST = 25`. 26 or more: "Sending to N people. It will show under Notices I sent when it is done." (decision 1's words) | Spec AC-30 annotated; test pins 25 |
| (b) | Sender list as drawn | Name, job title (the holder's Active Employee designation) and "Last changed by <name>, <date>", from the newest User history row that mentions Notice Sender. Empty lines are left out. No email, no user id | Python test (keys, title, Administrator as the changer); DOM test (title, the line, a hostile name as text). Spec AC-107 annotated |

**Re-measured (my site test076l, Administrator sending to chosen people):**

| Send | Page waits | Queries in the request | Background |
|---|---|---|---|
| Now, 25 people | 341 ms and 555 ms (two runs; the first colder) | 133 to 146 | none |
| Now, 26 people | 55 ms (two runs) | 9 | about 330 ms, 125 queries, status Sent |

25 people is around the 500 ms budget, not clearly under it. The rate is about 13 ms per person.

**Tests after the fix pass:** `test_announcements_076` 55 OK; `test_notices_076` 9 OK; `test_home_076` 6 + 18 OK; `test_portal_security_010` 45 + 5 OK; `test_grooming_066` 64 + 1 OK. DOM suite 18 files, 0 failed (the Part B file now 75 checks). `check_scope_traps.py`, `check_app_integrity.py`, `check_brand_spelling.py`, `check_design_system.py`, `check_tag_balance.py`, `check_api_paths.py`, `check_undefined_js.js`, `check_portal_handlers.js`: all OK.

**Still open:** AC-18 (above); the residual risks in 01c section 12 are still not accepted by name; DTC's live `mute_emails` value is still not read; the reviewer's P4 (two indirect forms the scope-trap script misses) is not touched. 01c's PRIV-8 still says "names only"; her decision (b) overrides it.

The sections below are the first write-up. Where they differ from this table, this table wins (the 200 limit, the role grant at install, the names-only list, the raw stored message).

## Bad news first

1. **"Send now" to 200 people takes about 3 seconds before the page answers.** Measured: 980 people took 14.4 s, which is about 15 ms per person (each Notification Log row is a full Frappe insert: the row, the "unseen" flag, the realtime push). The approved plan sends 200 or fewer inside the request. The budget is 500 ms for an API call, and our rule is "work over about 2 seconds goes to the background". Today the page shows the button switched off and waits; nothing breaks. **Decision for Surbhi:** keep 200, or send in the request only up to about 25 people (about 0.4 s) and put everything larger on the background queue with the "Sending to N people" line she already approved. Lowering it is one number (`SEND_IN_REQUEST`).
2. **The Organisation settings list of senders differs from the drawing.** The prototype shows each holder's name and job title, and a "Last changed by Kavita Rao, 20 Oct 2026" line. The approved spec (AC-107, PRIV-8) says "full names only". I built names only, and no "Last changed" line (in design section 7 that line belongs to the birthdays switch, which is Part C). **Needs her yes either way:** add the job title (a parity fix), or accept names only.
3. **Not for a live tenant yet.** There is still no retention number for notices and read marks (Q1). Nothing is deleted. That was her working default; it stays a release gate for DTC.
4. **The "1,200 people" send was measured with 980**, the largest site I have (sections below). 1,200 would take about 18 s by the same rate, inside one background job. The spec's estimate was "under about 10 s"; that estimate was wrong.
5. **I could not read DTC's own site config.** How email is muted there comes from the repo's runbooks, not from the server (section "Email at DTC").

## What was built, file by file

| File | What | Rung, and why not lower |
|---|---|---|
| `alvoraa_portal/alvoraa_portal/doctype/announcement/` (new) | The `Announcement` DocType, fields exactly as spec 5.1. Track Changes on. Notice Sender: create, read, write if owner. System Manager: full. Controller: refuses any insert that did not come through `create_notice` (the REST door would skip scope and limits); after insert, the only change allowed is Scheduled to Cancelled. | 5. Notification Log has no audience, send time or status (spec G7). |
| `alvoraa_portal/announcements.py` (new) | `notice_reach`, `search_notice_people`, `create_notice`, `cancel_notice`, `my_sent_notices`, `notice_sender_holders`, `send_due_announcements` (scheduler), `send_one` (the worker), `email_is_active`, `make_role`. | 4. |
| `hrms/hrms/alvoraa_hr_core/access.py` | One new function at the end, `notice_audience_conditions(user)`. Nothing else in the file changed. | 4. Changing `permitted_employee_filters` would widen other screens. |
| `alvoraa_portal/notices.py` | Announcement rows in the one feed: pinned first, the sender's label, the text unescaped for the page (it is stored escaped for the desk), and `can_send`. | 4, one function already serving the card and the bell. |
| `hooks.py` | Two lines: the scheduler line (`all`), and `make_role` in `after_install`. | See decision 3 below for the second line. |
| `patches.txt` + `patches/v1_0/notice_sender_role.py` | Makes the role with no desk access and gives it once to the users who hold HR Manager then. | 2. |
| `subscription.py` | `Announcement` named as tenant-side (the plan's one line). The billing test only reads `Alvoraa %` names, so this is documentation, not a test fix. | |
| `templates/includes/ess/parts/home.html` | The Compose panel (`panel-notice-compose`), after the Home panel. | markup |
| `templates/includes/ess/parts/org-settings.html` | The read-only "Who can send notices" card. | markup |
| `public/js/ess/portal.js` | A new `nc` block (Compose, Notices I sent, Cancel, holders). One-line edits: the Notices footer gets "Send a notice" when `can_send`; announcement rows show "Pinned" and the sender; the notice sheet title "Notice from …"; one line in the Home click handler; one call (`ncHolders()`) on the Organisation settings open line in `switchPanel`. | 4 |
| `public/css/ess/panels.css` | A new `nc-` block after the Home block, design tokens only. | CSS |
| Tests | New `tests/test_announcements_076.py` (51), new `alvoraa_portal/tests/portal_notices_send_076_test.js` (72 checks, registered in `scripts/run_dom_tests.js`, 17 to 18). `test_notices_076.py` changed on purpose: two new item keys (`kind`, `from`) and `can_send`. `test_portal_security_010.py`: three new ceiling rows at the end (`announcements.py` 1, the controller 0, the patch 0). | |

Not touched: `en.csv` (the DocType is called `Announcement`, not `Alvoraa …`, so the brand check has nothing to translate; it passes), `hrms-employee.html`, `inbox_api.py`, `deploy/`, `.github/`.

## Decisions I had to make (none changes what she approved; each is listed so she can overturn it)

1. **The REST door is shut.** A Notice Sender has "create" on the DocType (spec), so `POST /api/resource/Announcement` would have made a notice with no limits and no confirm. The controller refuses any insert that did not come through `create_notice` (a request-only flag, not something a client can send). A REST edit can only cancel. Test: `test_a_rest_insert_or_edit_does_not_go_round_the_checks`.
2. **The message is stored exactly as typed.** Frappe's own cleaner rewrote `<img src=x onerror=alert(1)>` to nothing, and its "required" check calls a message made only of tags empty. So the field skips Frappe's cleaner and "required" is checked by our controller. Safe because the text is escaped wherever it is shown (portal `esc()`, the desk copy and the email are HTML-escaped before they are written).
3. **A second hooks line, `after_install`.** On a brand-new tenant, patches do not run, and Frappe creates any role it finds in DocType permissions *with desk access*. A Notice Sender would then become a desk user. `make_role` sets desk access off after install; on live sites the patch does it before the DocType arrives. Nobody is given the role on a new tenant (no HR Manager exists at install), so the organisation gives it in Users.
4. **The sender does not get their own notice**, and is not counted in "This reaches N" (as Frappe's own notification code does for everything except its "Alert" type).
5. **A person's Desk "notifications off" setting is not honoured.** A notice is an organisation message. If honoured, a person could opt out of HR notices and "Reached N" would quietly shrink.
6. **Companies appear in the list only when the sender's scope has more than one** (as drawn: HR sees branches, the CXO sees companies and branches).
7. **"Everyone I can see" for a System Manager, "Everyone I look after" for everyone else** (the two labels drawn).
8. **"· Emailed" in Notices I sent** comes through the existing `reason` key, because AC-39 fixes the key list. It shows "Emailed" or "email not sent: email is off".
9. **The live reach line is worked out on the page from the counts the server sent once**, not by a server call on every change. The server checks the real number again at create.
10. **The cancel always writes a Version row**, also under tests (Frappe skips Version rows in tests unless asked), so PRIV-3's "who cancelled, and when" is proven, not assumed.
11. **A "Sending" notice counts a stall only when nothing was written for 10 minutes.** The counter goes back to 0 after every written chunk, so three stalls in a row end in Failed.

## Email at DTC (read only; I changed nothing)

From `docs/runbooks/2026-09-production-release.md` and `deploy/compose/docker-compose.app.yml`: production mutes email bench-wide. At container start, `bench set-config -gp mute_emails "$MUTE_EMAILS"` writes `mute_emails` into `common_site_config.json` from `MUTE_EMAILS` in `deploy/envs/production.env`. A single site can override it in its own `site_config.json` (the runbook names one site that does). `email_is_active()` asks Frappe's own `frappe.are_emails_muted()`, which reads the site value over the bench value, and then needs either an enabled outgoing Email Account or a `mail_server` in the config, which is where Frappe itself looks. **Not checked:** the live value at DTC. Someone with server access should read it before email is turned on there.

## Parity table (02-design.md section 14), the Part B rows

| # | Drawn feature | Built as drawn? |
|---|---|---|
| 12 | Notices card: pinned announcements first, alerts below, unread only, 5 rows, "N unread" equals bell | yes (Part A built the card; B adds Pinned, the sender's name, the order) |
| 13 | Notice sheet, full text, opening marks it read | yes: title "Notice from Kavita Rao", meta line with the full label (browser check) |
| 14, 15, 16 | See all, bell, empty states | unchanged from Part A, now include announcements |
| 17 | "Send a notice" only for holders | yes, absent (not greyed) for others; the server refuses them anyway |
| 21 | Message, counter, warning | yes ("212 of 300", the warning sentence) |
| 22 | Audience with live line | yes, the three options; the sentence word for word |
| 23 | Now or later, 4-minute hint | yes |
| 24 | Email tick only when email is active, unticked | yes |
| 25 | The button names what happens; sent-today line | yes; "Sending to N people…" for Now over 200 (her decision 1) |
| 26 | Confirm above 25 | yes, the dialog words and both buttons |
| 27 | 5-a-day screen | yes |
| 28 | Inline errors with focus | yes, the five sentences; `aria-describedby` set |
| 29 | Result line, Notices I sent with counts | yes, plus "· Emailed" (see decision 8) |
| 30 | Cancel a scheduled notice | yes, dialog "Cancel this notice?", "Keep it" / "Cancel the notice" |
| 31 | Organisation settings: holders list and where to change it | **differs:** names only, no job title, no "Last changed" line (bad news 2). "Open Users" opens the desk Users list in a new tab |
| 33 | The role given in Users | yes, no new screen |
| — | Decision 10, "It may have gone through. Check Notices I sent." | yes; the button stays off and the list is read again |

Not drawn but needed, so I added the plainest words: "You have not sent a notice yet." (empty list), "Nobody has the Notice Sender access yet." (empty holders list), "No one by that name in the people you can reach." (empty search).

## Acceptance criteria for B

| AC | Status | Proof |
|---|---|---|
| 1, 2 | met | `test_the_role_is_given_once_and_never_again`; on test076 the patch gave the role to all 18 enabled HR Managers, desk access 0 |
| 3 | met, **not a finding**: an HR Manager who is not System Manager cannot save a User with the role | `test_an_hr_manager_cannot_give_the_role` |
| 4 | met | `test_the_role_is_in_no_profile_and_no_default` |
| 5 to 13 | met | `TestScope` (9 tests), incl. the pin tests |
| 14 | met | Guest, plain employee, HR Manager without the role, on all five endpoints |
| 15 to 22 | met | `TestLimits`; AC-17's "two parallel fifth notices" runs two real database connections at once and gets exactly one |
| 23 to 35 | met | `TestScope`, `TestSend` |
| 36, 37 | met | `TestCancel` |
| 38 | met for both orders, run one after the other | true simultaneity is covered by the row lock, not by a timed race test |
| 39 to 43 | met | `TestNoticesISent` |
| 44 to 52 | met | DOM test (72 checks) |
| 53 to 56 | met | `TestEmail`; the "email off" tests set a mail server so only the mute makes email inactive |
| 57, 58 | met, three users with different data | `test_pinned_first_with_the_sender_and_the_bell_equals_the_card` (not literally "mid-send") |
| 62, 63 | met | Python and DOM |
| 64 | met | EXPLAIN on 100,000 rows: every query uses an index; no index added |
| 107 | met as specified (names only) | see bad news 2 |
| 117, 118 | met | `check_scope_traps.py` passes; ceilings in `test_portal_security_010` |
| 125 | partly | 980 people, not 1,200; times below |
| 122 to 124, 126, 127 | not this step | release and review checks |

## Tests run, and what they said

All Python in my own container, one module at a time. Where `bench run-tests` printed two batch summaries, both are shown.

| Module | Result |
|---|---|
| `test_announcements_076` (new) | 51 ran, OK |
| `test_notices_076` | 9 ran, OK |
| `test_home_076` | 6 OK, then 18 OK |
| `test_portal_security_010` | 45 OK, then 5 OK |
| `test_frame_endpoint_registry_034` | 9 OK |
| `test_invoicing` (the tenant-side list) | 4 OK, then 20 OK |
| `test_inbox_parts_042` | 25 OK |
| `test_employee_field_rights_alv215` | 20 OK |
| `test_grooming_066` | 64 OK, then 1 OK (after the rebase). Its first run failed one fence test on **my own scratch probe file**, which named the grooming record; I deleted the probe and it passes |

After rebasing onto `origin/dev` (two incoming commits), `test_announcements_076` (51), `test_grooming_066` (64 + 1) and `test_home_076` (6 + 18) were run again: all OK. DOM suite and static checks again: all OK.

- **Each guard was broken on purpose once, and its tests failed:** the job resolving scope as Administrator (8 tests failed, including the pin test), a director with no Company permission let in (3), notice rows not of type Alert (26), no lock on today's count (the parallel test failed), no skip of people who already have a row (2), email ignoring the mute (2, after I tightened those tests: at first they passed for the wrong reason). Every file was restored and the clean module passes again.
- **A trap I hit, worth knowing:** after restoring a file of the same size within the same second, Python kept the broken compiled copy, so later runs failed for no reason in the code. Clearing `__pycache__` fixed it.
- DOM suite (`NODE_PATH` borrowed from the 063 worktree): **18 run, 0 failed**; the new file 72 of 72; Part A's file 77 of 77.
- Static checks, all OK: `check_scope_traps.py`, `check_app_integrity.py` (854), `check_brand_spelling.py`, `check_design_system.py`, `check_tag_balance.py`, `check_api_paths.py --max 0`, `check_undefined_js.js`, `check_portal_handlers.js`, `check_portal_trays.js --static`, `check_day_widget.js`.
- **Not run:** the whole app suite (CI runs it; it is due once before the dev push), other slices' modules.

## Real browser (Chrome, my site test076 at 127.0.0.1:8076)

- As branch A's HR (Notice Sender): the Notices card showed "Send a notice"; Compose showed "Everyone I look after (3 people)"; "Chosen people" listed exactly the three people of branch A; ticking two gave "This reaches 2 people…" and the button "Send to 2 people"; sending gave "Sent to 2 people. They will see it on Home and in the bell." and "Reached 2 people · Read by 0 of 2". A notice scheduled for 3 Nov showed "Not sent yet" and "Cancel this notice"; the dialog cancelled it; the list then said "Cancelled, not sent". In the database: two rows of type Alert, one Version row for the cancel, no email queued.
- As Asha (a recipient): the card showed "1 unread", "Pinned · Hra N076"; tapping opened "Notice from Hra N076" with the full label; the row became read and the card said "You are up to date". No "Send a notice" for her. No console errors.
- **Seen and not caused by B:** Asha's Pending card showed its failure box, because her test login had lost the Employee role (ERPNext removes it from a login saved before an Employee points at it; `origin/dev` commit 9c5a5c63 fixed the same thing in Part A's tests). I fixed my fixture the same way.

## Measurements (my sites; query counts are the proof, times are a record)

| Call | Before (Part A) | After |
|---|---|---|
| `notices_feed` card | 2 queries | 2 queries (3 ms) |
| `notices_feed` See all with an announcement | 2 | 3 (one read of the senders' names) |
| Feed for one person with 100,000 Notification Log rows on the site | | 3 queries |
| `notice_reach` / `my_sent_notices` / `search_notice_people` | new | 4 / 3 / 3 queries |
| `create_notice`, Now, 3 people (in the request) | new | 50 queries, 335 ms |
| Send to 980 people (`send_one`, background) | new | 14.4 s, 3,998 queries (about 4 per person), 7 commits, 2.2 MB peak memory |
| Kill after 2 chunks, then resume | | 400 rows kept; after resume 980 rows, 980 distinct, status Sent |
| EXPLAIN, 100,000 rows | | feed: index `for_user`; skip-existing: index merge `for_user, document_name`; count: index `document_name`. No index added |

## The seven dimensions, against the code I wrote

| Dimension | Before to after | Why |
|---|---|---|
| Performance | neutral on Home; **degrades on "Send now"** | The feed stays at 2 queries. A Now send to 200 holds the request about 3 s (bad news 1). Large sends are background work |
| Security | degrades by design, then held | A new way to reach many people. Held by: role check on every endpoint, scope as a list worked out as the sender, the job naming the sender everywhere, the REST door shut, rows of type Alert, escaping before storage. One `ignore_permissions` (writing other people's rows) |
| Reliability | improves on plain inserts | Row lock first, chunk commits, skip-existing, resume after 10 minutes, Failed after 3 stalls, Not sent with a reason; a lost answer never sends twice |
| Scalability | degrades | One Notification Log row per person per notice, with no purge yet (Q1) |
| Maintainability | degrades a little | One DocType, one module, one block in `portal.js`. No new abstraction |
| Data integrity | improves | A notice goes once; the audience is fixed at send time; the record cannot be edited after it is made |
| Compliance and privacy | degrades until Q1 has a number | Counts never names; the record answers "who sent what to whom"; no message text in any log |

## What else moved while I worked

- Start: the branch equalled `origin/dev` (db04a812).
- After my code commit, two commits had come in: `9c5a5c63` (Part A tests give the Employee role back; `test_home_076.py` only) and `7094d9c3` (slice 065: the plan's Save button sends the tick; 065 files only). Neither touches a file I changed (065 changes `portal.js` in its own block). I rebased onto them with no conflict; my code commit is `ed0274b3`.
- I did not touch the main checkout.

## Known gaps

| Gap | Label |
|---|---|
| "Send now" to 200 holds the request about 3 s | **for Surbhi to decide** (bad news 1) |
| Holders list: names only, no "Last changed" line | **for Surbhi to decide** (bad news 2) |
| No retention for notices and read marks | temporary debt; a counsel number removes it (Q1). Not for a live tenant until then |
| A new tenant starts with nobody holding Notice Sender | intentional: there is no HR Manager at install; the organisation gives it in Users |
| The DTC email setting is read from the runbook, not the server | to check before email is turned on there |
| The "1,200" measurement used 980 people | acceptable simplification, rate given |
| Cancel and send racing: proved by the lock and by tests run one after the other, not by a timed race | acceptable simplification |
| Measurement data left on my sites: 912 throwaway logins and 100,000 Notification Log rows on `test076l`; test notices on `test076` | remove with the sites |

## Subtract pass

Removed: the spec's `notice_mark_read` (Part A already uses Frappe's `mark_as_read`); a server round trip for the live reach line (the page has the counts); `ignore_permissions` on the role insert (the patch and install run as Administrator); a separate "sender label" query in the card (one read, only when announcements are shown). Kept, and why: the REST guard in the controller (without it the limits are client rules), the `after_install` line (without it a new tenant's senders become desk users), and the per-chunk email (D4, US-9).
