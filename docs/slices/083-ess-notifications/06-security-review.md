---
slice: 083-ess-notifications
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-12
status: review — for Surbhi, alongside the techno-functional review and release readiness
head: 45e9b1c7 (8 commits, rebased on origin/dev at 75149184)
inputs: [01c-security-privacy-requirements.md, 00-impact-analysis.md, 02-functional-spec.md, 03-implementation-notes.md, 07-devops-inputs.md, 08-dtc-counts.md, git diff origin/dev...HEAD, Frappe 16.x source inside a83-bench, read-only queries against a83-bench test_site]
---

# 083 · Security and privacy review

## Answer first

**No P0. No Blocker. Ten of the twelve requirements are met. Two are partial, and
neither is a reason to stop the slice.**

The two riskiest lines in this slice — the uncapped count and the bulk write — are
built exactly as SEC-1 and SEC-2 asked, and both now have **executed** tests behind
them. That was the whole security story of this slice on 6 November and it has come
out right.

What is partial:

| # | Requirement | What is missing | Rank |
|---|---|---|---|
| **F-1** | **SEC-6** | The control is in the code and I verified it. **Two of the tests the requirement named do not exist**: nothing asserts that Guest is redirected away from `/hrms-employee`, and nothing asserts `context.no_cache = 1`. So a future edit that drops one line ships silently onto the one page that now holds 30 days of a person's HR messages on a shared handset | **P2** |
| **F-2** | **SEC-7(b)** | The Chrome-on-Android Back-after-logout check has still not been run. This is risk R5, already named as a release gate. **I am not marking it met, and nobody should write it down as met** | **P2 · release gate** |

**One thing to say out loud before anything else: at DTC the notices half of this page
is invisible.** `08-dtc-counts.md` is clear — DTC holds **zero** rows of all three
notice kinds. So after release the bell's number at DTC comes entirely from work owed,
"Mark all as read" matches nothing, and **every control in this slice that is about
notices is unobservable on real DTC data.** It can only be seen working on the seeded
test site. That is slice 028's lesson and it applies here in full: a clean run at DTC
would prove nothing about the notices half.

**The one control that *is* observable at DTC is the one that matters most.** DTC
carries **902 unread `Employee` notification rows**, every one unread. If the bulk
write had been Frappe's own `mark_all_as_read`, one tap by an HR user would have
cleared their share of those 902 rows, silently and unlogged. It is not, and the
second of the three write assertions proves it. That assertion is backed by a real
number now, not a prediction from PPJ.

**Declarations, because they matter more than the verdict.**

1. **I wrote `01c`, so I am checking my own requirements.** I have tried to be harder
   on them than on the code.
2. **I wrote AC-55 (`TestTheDoorsToSomebodyElsesNotices`), so I am also reviewing my
   own test.** I have audited it below, found three things wrong with it, and none of
   them is fatal — but **`hrms-technofunctional-reviewer` should take that test and the
   `mark_all_seen` move**, because I proposed both. That is the same request I made on
   6 November and it still stands.
3. **I ran nothing against dev, DTC or production.** Everything I executed was
   read-only, on `a83-bench`'s `test_site`, rolled back. Details in §7.

---

## 1 · Every SEC and PRIV requirement

"Met" means I can name the line of code and the test. Nothing here rests on a document.

| # | Verdict | The mechanism in the diff | The test that proves it |
|---|---|---|---|
| **SEC-1** · true count protected by its own `for_user` | **met** | `notices.py:118–122`. The count is `frappe.db.count("Notification Log", {"for_user": user, "document_type": ANNOUNCEMENT, "read": 0})` plus a sum over `open_alerts`, and `open_alerts` (`notices.py:97–101`) is `frappe.get_list` — permission-checked — with `for_user`, `read` and `document_type` all named. **No `frappe.get_all` anywhere in `notices.py`** for this doctype (verified by grep and by the test's own source assertion) | `test_the_count_is_the_caller_s_own_and_is_smaller_than_the_site_s` (behaviour) **and** `test_the_rows_are_never_read_with_get_all` (source). Both executed, `test_notices_076` **27 OK** |
| **SEC-2** · bulk write bounded to caller and the three kinds | **met** | `notices.py:177–182`. One `frappe.db.set_value` with `{"for_user": user, "read": 0, "document_type": ["in", list(NOTICE_DOCTYPES)]}`, `update_modified=False`. Not Frappe's `mark_all_as_read`. Not a loop. No arguments | Three **separate** tests, so a failure names its cause: `..._one_every_notice_of_the_three_kinds_is_read`, `..._two_my_own_desk_notifications_are_untouched` (AC-31), `..._three_a_colleague_s_notices_are_untouched` (AC-32). Plus one-statement, run-twice, no-arguments and Guest-refused. All executed |
| **SEC-3** · no client-supplied filter, doctype, field or user | **met** | `mark_all_seen()` has an empty parameter list; `notices_feed(see_all=0)` still takes one `cint`-ed integer; `NOTICE_DOCTYPES` is a module constant (`notices.py:41`) and the write's filter **is** that constant, so the feed and the write cannot drift apart | `test_it_takes_no_arguments_at_all` uses `inspect.signature` and then checks a Desk row and a colleague's row are still unread. **The endpoint count: I counted it myself** — `@frappe.whitelist` in `alvoraa_portal` is **380 on `origin/dev` and 380 at `45e9b1c7`**. One deleted, one added, net zero. *Verified by running `git grep -c` on both revisions.* **There is no standing CI assertion on that count** — see P4-5 |
| **SEC-4** · no bypass added | **met** | `grep -c ignore_permissions alvoraa_portal/alvoraa_portal/notices.py` → **0**. No raw SQL added — the diff adds no `frappe.db.sql`. No new `.py` file, so no new ceiling is needed | The existing ceiling test carries `("alvoraa_portal", "notices.py"): 0` (`test_portal_security_010.py:748`) and it strips docstrings before counting, so the new 30-line docstring cannot game it. `test_portal_security_010` **45 + 5 OK** |
| **SEC-5** · the Frappe door list is a test, not a memory | **met** | No code change was needed; the requirement was a test | `TestTheDoorsToSomebodyElsesNotices` (`test_notices_076.py`). Nine doors, not six: list, hostile `for_user` filter, `reportview.get`, `reportview.get_count`, `client.get_list`, `client.get_count`, `client.get_value`, link search, `client.get` of a named row (refused), and `reportview.export_query`. Seeds rows for **three** people in `setUp` and asserts the caller's own rows come back **before** asserting the others do not — so it cannot pass on an empty table. **Audited in §2** |
| **SEC-6** · page stays behind the session, at no new address | **partial · P2 (F-1)** | All four controls are present and I verified each: Guest is redirected before any context is built (`www/hrms_employee.py:9–11`); `context.no_cache = 1` (`:12`); the route is a hash inside the same page — `deploy/nginx.conf` is **not in the diff** and no new `www/` page was added; the portal service worker is still `function (e) { return; }` with no `respondWith` (`field_app_pwa.py:407`) and **`field_app_pwa.py` is not in this diff at all** | **The service-worker pin is real and still holds**: `test_portal_pwa_062.py:280–281` asserts `_PORTAL_SERVICE_WORKER` contains none of `caches`, `cache.put`, `respondWith`, `CacheStorage`, and `:302` asserts the worker is served `no-cache, no-store, must-revalidate`. **But nothing tests the two things the requirement named** — the Guest redirect and `context.no_cache` for this page. I grepped every test that mentions `hrms_employee`; `test_preview_page_034` asserts `no_cache` for a *different* page |
| **SEC-7** · the handset leaves nothing for the next person | **partial · P2 (F-2)** | **(a) met, and by more than the test claims.** I grepped the whole of `portal.js` (24,575 lines): the only client-storage call sites are `localStorage.getItem("sb-pinned")` at `:24570` and `setItem` at `:24578`. Nothing else. No `sessionStorage`, no `indexedDB`, no `caches.` anywhere in the file. Both sign-out links already clear `sb-pinned`. **(b) not met, and openly open** | (a) `portal_notifications_083_test.js:375` asserts the new block's code — **comments stripped first**, which is the right way round — names no storage API. (b) **The Android check has not been run.** Risk R5 stays open. The fallback if it fails is still the one line on `pagehide`, named in `01c` §6, and still not written — correctly |
| **PRIV-1** · the field set is frozen, and the page proves it | **met** | `inbox_api.py` **is not in the diff**, so `ROW_KEYS` is untouched. `notices_feed` gained exactly **one** key, `capped`. No DocType `.json`, no Custom Field fixture in the diff. **Checked against the real field list, not the prose — see §3** | The exact key-set assertion at `test_notices_076.py:65` now reads `{"unread", "capped", "any", "can_send", "items"}` — extended, not loosened. And the stronger one, pre-existing and executed today: `test_inbox_parts_042.py:588` asserts, per part and per row across four logins, that `sorted(row.keys()) == sorted(row_keys(part.key))`, guarded by `assertGreater(seen, 0)` so it cannot pass on no rows |
| **PRIV-2** · no absence explanation, health, passport, bank, pay figure or salary; a leaver reaches nothing | **met** | `explanation` is still absent from `ROW_KEYS` (`inbox_api.py:152` lists `reason`, the fixed-option category, not `explanation`), and the page draws neither — `hmRowView`'s `attendance_fixes` branch (`portal.js:6782`) draws name, dates and the waiting line only | **Met by a stronger mechanism than the one I asked for.** I asked for a named-field assertion; what exists is the exact per-part key-set assertion above, which makes `explanation` — or a salary, bank or passport field — impossible to add without turning that test red. Leaver: `test_inbox_parts_042.py:302` `test_a_leaver_with_a_live_login_gets_zeroes`; `test_grooming_066.py:1061` "HR who left reads nothing" and `:408–409` a `Left` HR User and a `Left` manager; and **new in this slice**, `test_the_count_ignores_a_notice_whose_mark_the_reader_may_no_longer_read` sets the reader to `Left` and asserts the count **and** the list both fall to zero |
| **PRIV-3** · no identifier anywhere a browser keeps it | **met** — structurally, and more strongly than the test | `switchPanel` writes `window.location.hash = "#" + name` where `name` is a panel word (`portal.js:4766`), and `panelFromAddress` (`:4688`) accepts a hash only if it matches `^[a-z0-9-]{1,40}$` — so a record id in the hash is not merely absent, it is **unreadable**. No `pushState`, no state object, and nothing on this page writes `document.title` (the only `document.title` writes in the file are the wall chart's, `:4017`, `:4076`) | **The assertion in the JS test does not prove its claim** — see P4-3. The mechanism does. I am marking this met on the code, and flagging the test |
| **PRIV-4** · read state stays with the recipient | **met** | `mark_all_seen` returns `{"ok": 1}` and nothing else. The count returns an integer. `notices_feed` items carry `name, kind, from, text, link, when, read` for the caller's own rows only. The one endpoint this slice revived, `get_nav_counts` (`inbox_api.py:1114`), returns **counts and routes only** — its own docstring says "no names, no reasons, no document ids (PRIV-4)" and I read the return: it is true. No read-receipt field, report or endpoint anywhere in the diff | The return shapes are asserted by the key-set tests above; the absence is verified by reading the whole diff. `test_inbox_parts_042` **32 OK** |
| **PRIV-5** · the retention gap is written down, not hidden | **met as specified** — it was never a test | The spec carries it (`02-functional-spec.md` §14 and the data table at line 860), and the implementation notes repeat it as **G-13**. Risk **R1 was accepted in writing by Surbhi on 6 November 2026**, dated, **for this slice only and explicitly not a standing waiver** | Not testable, by design. The purge engine (feature map **A6**) is still unbuilt and still the PM's to slice |

---

## 2 · Audit of AC-55 — my own test, checked rather than trusted

You asked me not to take it on trust. Three things, and one independent proof.

**It is not vacuous, and I proved that by running it.** Read-only, on `a83-bench`'s
`test_site`, today, rolled back:

- `rahul@g066.test` (roles `Employee`, `All`, `Guest`, `Desk User`) holds **36**
  `Notification Log` rows. Through `frappe.get_list` he sees **36**. Through
  `search_link("Notification Log", "", page_length=50)` he gets results back — a real
  list, with `value`, `label` and `description`, and **`description` is the row's
  subject text**.
- Three other logins, including **two HR Managers** (`s010.hr.other@example.com`,
  `s010.hr.self@example.com`), see **0** rows through the list door and **0** through
  link search.

That last line is worth more than the test: on 6 November I asserted the HR Manager
case from reading Frappe's permission condition. **It is now verified by running it.**
Link search is also the door I was least sure about, and it is the one that returns
the message text — it is closed, and it is closed by the same `for_user` pin.

**Three faults in my test, none fatal.**

| # | Fault | Rank |
|---|---|---|
| **P3-1** | **The link-search assertion is negative-only.** It asserts the two colleagues' row names are absent. It never asserts the caller's own row is **present**. If a Frappe upgrade made link search return nothing at all for this doctype, the assertion would pass and prove nothing — exactly the trap the rest of the test avoids. I have proved by running it that the door does return rows today, so the hole is theoretical now and permanent later. **Fix: one line** — `self.assertIn(self.mine, names)` | **P3** |
| **P4-1** | **The export assertion is sound but not hermetic.** It does prove what it claims: `export_query` → `_export_query` → `provide_binary_file` sets `frappe.response["filecontent"]` to the CSV **bytes** (`frappe/desk/utils.py:84–86`, read in the running bench), and reading every string and bytes value in `frappe.response` therefore reads the CSV whatever the key is called. The positive `assertIn("Mine", body)` is what anchors it — if the key moves or the call returns nothing, that assertion fails **loudly** rather than passing quietly, which is the safe direction. The hole: `frappe.response` is **not cleared first**, so in principle a value left by an earlier call could satisfy the positive assertion while the export itself returned nothing. **Fix: one line** — set `frappe.local.response = frappe._dict()` before the call, or assert `frappe.response.get("type") == "binary"` | **P4** |
| **P4-2** | **A docstring points the next person at the wrong assertion.** `test_the_count_is_the_caller_s_own...` says "delete it and this fails on the second assertion". It does not. With `for_user` dropped from the count, Rahul's total becomes 1 (his own grooming notice) + 1 (Olga's site-wide unread announcement) = **2**, so `assertEqual(mine, 1)` — the **first** assertion — fails, and `assertLess(2, 3)` still passes. The test is right; the comment sends the next reader to the wrong line. Lesson 5 in my own instructions is exactly this | **P4** |

**On "I proved SEC-1 by breaking it, and two tests went red independently" — I confirm
that, and it is genuine, not two views of one thing.** The two failures come from two
different sources of truth:

- `test_the_count_is_the_caller_s_own_and_is_smaller_than_the_site_s` fails on the
  **data** — because the fixture deliberately plants an unread announcement for Olga,
  so a count without `for_user` returns a bigger number. Remove Olga's row and this
  test loses its power; keep it and it is real.
- `test_the_rows_are_never_read_with_get_all` fails on the **source text** — it reads
  400 characters after `frappe.db.count("Notification Log"` and requires `"for_user"`
  in them.

One is behaviour, one is spelling. They cannot both pass with the term gone. *This part
is inference from reading both tests and the code — I did not re-run the mutation
myself, because that would mean editing product code on a shared bench.*

**A fourth point, in the test's favour.** Using `get_list` rather than `get_all` is the
difference between testing Frappe's permission check and testing nothing. You caught
that on yourself. The product code makes the same choice at `notices.py:84` and `:97`,
and the test now pins it in source. That pairing is the strongest thing in the slice.

---

## 3 · PRIV-1 against the real field list

I checked the page against `ROW_KEYS` as it exists in `inbox_api.py:112–167`, field by
field, not against the design's six-word summary.

**The spec's parity table is an exact match to the code.** All seven parts, every field,
same order (`02-functional-spec.md:271` onward). `context`, `note`, `reason`,
`has_bill`, `can_decide`, `can_withdraw`, `says`, `state`, `title`, `subject`, `value`,
`logged_on`, `document`, `half_day`, `lwp_in_play`, `lwp_limit`, `special_day` and
`chain_top` are all there and all classified. That is what I asked the analyst for on 6
November and it was done.

**What the page actually draws is a strict subset.** `hmRowView` (`portal.js:6662–6691`)
is the one function that turns a row into words, and the new page reuses it unchanged:

| Part | Drawn on the new page | Not drawn anywhere |
|---|---|---|
| `leave_approvals` | `employee_name`, dates, `total_days`, waiting line | `context`, `half_day`, `lwp_in_play`, `lwp_limit`, `special_day`, `chain_top` |
| `expense_approvals` | `employee_name`, `amount`, `expense_type`, waiting, `has_bill` **as words** | `note` (sheet only) |
| `goal_updates` | `employee_name`, `kind`, `subject` | `value`, `logged_on`, `document` |
| `attendance_fixes` | `employee_name`, dates, waiting | **`reason`**, `context`, `can_decide` |
| `shift_requests` | **nothing** — skipped in `hmPendingRows` and in `ntWorkOwed` (`NT_SKIP`, `portal.js:6432`) | all |
| `policies` | `title`, `version` | — |
| `my_requests` | `title`, dates, `says` | `note`, `state`, `can_withdraw` |

**So the page widens nothing, and it narrows one thing:** `reason` on an attendance fix
reaches the browser and is drawn on no portal surface. The decision sheets
(`hmLeaveSheet`, `hmExpenseSheet`) are untouched by this diff and add only
`leave_type` and `note` — both already classified.

**One pre-existing finding this check turned up, and it is not this slice's to fix.**
Five slice-063 fields — `half_day`, `lwp_in_play`, `lwp_limit`, `special_day`,
`chain_top` — are sent to the browser on every leave row where a pay rule set is on,
and **no portal surface renders any of them.** `lwp_in_play` is the "N of 5 unpaid days
used" figure about a colleague, which is the most pay-adjacent thing on any row. On 6
November I argued it should stay because it is the thing being decided; having now read
every render path, **it is not shown to the person deciding.** That is data reaching a
browser for no purpose. **P4, routed to `hrms-business-analyst` for slice 063's owner,
not a requirement here** — this slice does not touch `inbox_api.py` and should not start.

---

## 4 · The `share` finding — does this slice change the picture?

**No. And it still deserves to be left alone. One piece of new evidence makes the case
stronger, not weaker.**

What this slice does to it: nothing. The diff contains no `DocShare`, no `share` call,
no permission `.json`, no `Custom DocPerm` fixture. `Notification Log`'s permission row
— role `All` with `read, report, export, print, email, share` — is untouched.

The mechanism is unchanged and still counter-intuitive, so it stays written down: in
`frappe/permissions.py`, `has_permission` falls through to `false_if_not_shared()` when
the hook says no, so a `DocShare` row **overrides** our `has_permission` hook for the
**single-document** door. A person can disclose **their own** notice row to a colleague.
Nobody can share anyone else's — `has_permission(..., "share", doc=<colleague's row>)`
returns `False`, and AC-55 now asserts that.

**The new evidence closes the "should know" question I left open in `01c` §11.** The
list door opens to shared rows only when `_fetch_shared_documents` turns on, which needs
a User Permission on one of the doctype's own link fields. `08-dtc-counts.md` §5 reports
DTC's User Permission rows: **694 `Employee`, 42 `Branch`, 3 `Company`, 1 `Page`**.
`Notification Log`'s link fields are `type`, `document_type`, `source_doctype`,
`for_user`, `from_user`. **No overlap.** So the list door is shut at DTC as well as at
PPJ, and the shape of DTC's permission rows is the deliberate narrow per-doctype pattern
already on record.

**Still R3, still P4, still reversible with one `Custom DocPerm` if it ever matters.**
And still honest about its limit: I proved the mechanism in Frappe's source and proved
the list door closed by running it. **I have never created a real `DocShare` row on a
`Notification Log`, so the single-document render remains inference from source.** That
has not changed and I am not going to claim otherwise.

---

## 5 · The service worker — is the pin real, and does it still hold?

**Yes to both, and this is the control I would least like to lose.**

- `field_app_pwa.py` **does not appear in this diff.** The worker body is still
  `self.addEventListener('fetch', function (e) { return; });` with no `respondWith`
  (`field_app_pwa.py:407`). It caches nothing.
- It is served with its own `Cache-Control: no-cache, no-store, must-revalidate`
  (`:427`) and `Service-Worker-Allowed: /hrms-employee` — **not `/`**, which is the
  right scope and is commented as such.
- The pin is a real test, and it is pre-existing rather than written for this slice:
  `test_portal_pwa_062.py:280–281` forbids `caches`, `cache.put`, `respondWith` and
  `CacheStorage` in the worker body, and `:302` asserts the no-store headers.
- The file even carries a standing warning: before anyone adds caching, the build
  version must be inside the worker body and a kill switch must exist.

**One caveat, said plainly: `test_portal_pwa_062` is not one of the four suites run for
this slice.** It is in the app's suite and CI runs it, but nobody re-ran it today. The
claim rests on the file being unchanged, which I verified from the diff, not on a fresh
green tick.

---

## 6 · Shared handsets — where each of the three criteria stands

| Criterion | Where it stands |
|---|---|
| **No identifier in the hash route (PRIV-3)** | **Met, structurally.** `#` + a panel word, and `panelFromAddress` refuses any hash that is not `^[a-z0-9-]{1,40}$`. A record id cannot be put there and would not be read if it were |
| **Nothing in `localStorage`, `sessionStorage`, IndexedDB or the Cache API (SEC-7a)** | **Met.** Two call sites in the whole of `portal.js`, both `sb-pinned`, both cleared by both sign-out links. Verified by grepping the built file, not by reading the new block alone |
| **The `no-store` header assertion is in a test** | **No. It is not.** This is F-1. The header is right — `context.no_cache = 1` is set, `can_cache()` is therefore false, and Frappe's `process_response` applies `NO_CACHE_HEADERS` by `setdefault` to every response — but **nothing in CI will notice if that line is deleted.** I asked for this assertion precisely because the page became durable, and it did not get written |
| **Back after `/logout` renders nothing (SEC-7b)** | **Unproven, and I am saying so rather than marking it met.** Risk **R5** stays open. It needs one real Android handset, ten minutes, and the Chrome version recorded. If it shows rows, the fix is the one line on `pagehide` — named in `01c` §6, deliberately not written yet |

---

## 7 · Findings, ranked

No P0. No Blocker. **Nothing here requires a line of the product to be rewritten.**

### P2 — fix before release, or accept in writing with a name and a date

**F-1 · SEC-6's two assertions do not exist.**
*Scenario.* Six months from now an engineer tidying `www/hrms_employee.py` removes
`context.no_cache = 1` — it looks like a leftover, because nothing explains it and
nothing tests it. The full suite stays green. `/hrms-employee#notifications` then
becomes cacheable, on a page holding 30 days of one named person's HR messages, on
handsets 441 DTC logins share. Nobody finds out until a customer tells us.
*Fix, and it is small.* One test with two assertions, next to the ones that already
exist: call `hrms_employee.get_context` as `Guest` and assert `frappe.Redirect` with the
`/alvoraa-login?redirect-to=/hrms-employee` location; call it as a plain staff login and
assert `context.no_cache == 1`.
*Owner:* `hrms-test-automation-engineer`. *Label:* **temporary debt** — one test removes
it.

**F-2 · SEC-7(b) is still unrun.** Risk R5. Not new, not softened, and it is the one
thing in this slice that could become the front-page story the brief wrote out.
*Owner:* `hrms-test-automation-engineer` to run; **Surbhi** if it fails.
*Label:* **dangerous debt until the check is done** — which is why it is a release gate
and not a note.

### P3 — after release, tracked

**P3-1 · AC-55's link-search assertion is negative-only.** One line fixes it:
`self.assertIn(self.mine, names)`. I proved by running it that the door returns the
caller's own rows today, so the test is meaningful now; without the positive assertion
it can go quietly vacuous on any upgrade. *Owner: me.*

### P4 — note it

| # | What | Label |
|---|---|---|
| **P4-1** | The export assertion does not clear `frappe.response` first. Sound today, not hermetic | temporary debt |
| **P4-2** | `test_the_count_is_the_caller_s_own...`'s docstring names the wrong assertion | security debt (a wrong explanation sends the next person to the wrong line) |
| **P4-3** | **PRIV-3's JS assertion cannot fail.** `yes(/#notifications\|"notifications"/.test(SOURCE), ...)` is true of any version of the file, including one that also builds `"#notifications/" + name`. The claim is right; the assertion does not test it. A real one: assert the file contains no template or concatenation that puts anything after the word — e.g. nothing matching `#notifications` followed by a `+` or a `${`. The mechanism (`panelFromAddress`'s regex) is the actual control | security debt |
| **P4-4** | Five slice-063 pay-adjacent fields reach the browser and are drawn nowhere (§3). **Not this slice's file.** Routed to `hrms-business-analyst` | pre-existing debt |
| **P4-5** | There is no standing CI assertion on the number of whitelisted endpoints in `alvoraa_portal`. SEC-3 asked for one; what exists is `docs/security/whitelisted-endpoint-review.md` and my count today (380 → 380). I am **not** asking for a new gate — `check_api_paths.py` already fails on a path that does not resolve, which is the failure that actually bites | acceptable simplification |
| **P4-6** | `test_grooming_066._wipe` now deletes **every `Announcement` `Notification Log` row** on the site, not only the fixture's. Correct for a test site and necessary for test isolation, but it is a widened destructive fixture: run that suite against a tenant site and it would delete real announcement notification rows. One more reason the suite belongs on `test_site` only | intentional trade-off — say it once, in writing |
| **R4** | `inbox_api.py` holds one `ignore_permissions` and has **no CI ceiling**, so a second could land unnoticed. Carried from `01c`, still open, still not this slice's file | security debt — mine, routed |
| **R7** | The DPDP and CERT-In entries in `security-compliance-baseline.md` are dated **24 August 2026** and **go stale on 22 November — ten days away.** Mine to re-verify, and it must not be discovered inside the next slice | security debt — mine, dated |

### Worries — concerns I cannot yet write as *this actor, calling this path, sees this data*

1. **`open_alerts` is an uncapped read** (`notices.py:101`, `limit_page_length=0`). Three
   fields, one person's own rows, and the gate it feeds adds no queries — but the row
   count has no ceiling, and the `IN` list it builds into `_readable` grows with it.
   **What must exist to observe it:** grooming switched on at a tenant and a single
   person carrying thousands of unread marks. DTC holds **zero**, so it is unobservable
   today. Not a finding. Named so the next person does not have to rediscover it.
2. **`get_nav_counts` has never been measured in DTC's configuration** (G-11, OPS-40).
   A performance worry, not a security one, and DevOps owns it.

---

## 8 · What this slice introduced that my 6 November requirements did not anticipate

This is the part worth your time. Six things. **None of them changes who may see what**,
and I checked each rather than assuming.

**1 · A second start-up call went live on every non-Home page load.** `get_nav_counts`
(`inbox_api.py:1114`) had **no caller** before this slice; `ntBellBoot` now calls it. My
requirements were written for "one new read and one new write" and there are effectively
three live server calls behind the bell. **I read it rather than trusting its age:** it
refuses Guest, it is computed from the same `parts()` scope every other surface uses, and
it returns **counts and routes only** — no names, no reasons, no document ids. No
entitlement change. But it is worth stating that this slice **revived an endpoint nobody
had looked at recently**, and that is a shape to watch for: a caller-less endpoint is an
unreviewed endpoint.

**2 · A rate limit on the write, which nobody asked me for.**
`@_limited(SELF_KEY, "user", limit=30)` on `mark_all_seen`. It is a good addition and I
would have missed it. I checked what it stores: the wrapper puts
`sha256(frappe.session.user)` into `form_dict["self_user_key"]`
(`field_app_limits.py:71–73`), so the bucket is **per person** and not one shared bucket
— and what reaches Redis is a hash, never the address. The field name contains `key`,
which is what makes Frappe's own error-snapshot redaction mask it
(`field_app_limits.py:39–43`). On refusal, `refuse(...)` **raises** rather than returning,
so the portal's error branch runs and the screen cannot falsely report success. One
consequence: the field app's refusal vocabulary (`TOO_MANY_TRIES`, `retry_after_s`) now
appears on a portal endpoint. No personal data in it.

**3 · The person's own open requests became their own group, on Home as well as the new
page.** `hmOwnRows` / "Waiting on someone else · not counted". My data inventory covered
the `my_requests` fields but did not anticipate a new **group**. It is the caller's own
data, no new field, excluded from the badge (`NT_SKIP`), and static on the new page. No
exposure change — but it is a visible change to Home, which `01c` treated as untouched.

**4 · The desktop bell is now injected into Frappe's Desk navbar at boot**
(`nfHomeTheBell`, `portal.js:7329`). I reviewed a mobile-only bell. It is one node moved
in the DOM and it carries no data beyond a number and the words "Notifications, N
waiting". The engineer kept the **declaration** in our own `frame.html` precisely so our
own gates can see it, and wrote down why. That is the right call and I would not change
it.

**5 · The notifications panel markup is pasted into the page for every login**
(`www/hrms-employee.html` + `ess_part("notifications")`). All 23 panels already are, and
what puts one out of reach is only that its nav item is not shown — `mayOpenPanel`
resolves a panel by finding a **visible** nav item. **The new nav item has no role gate,
so every portal login can open this page.** That is intended and it is safe, but it
should be said in one sentence rather than left implied: **there is no permission on this
page at all. The whole of the scope lives in the two endpoints**, and both are
self-scoped with no arguments a browser can set.

**6 · A test fixture grew teeth.** `test_grooming_066._wipe` now deletes all
`Announcement` notification rows site-wide. See P4-6.

**And one piece of documentation that is now out of date, which matters because people
read it as the record:** `03-implementation-notes.md` G-1 and G-2 both say "dangerous
debt — escalating": the Python suite had not run, and AC-55 was not written. **Both are
now closed** — the four suites ran green today and AC-55 exists. The notes should carry
a dated line saying so, otherwise the slice's own record contradicts its review.

---

## 9 · Compliance verification

| Obligation | Source and the date I last verified the source | Engaged here? | Verdict |
|---|---|---|---|
| **Reasonable security safeguards — access control** | DPDP Act 2023, via `security-compliance-baseline.md` §2, **24 Aug 2026** | Yes | **Met.** The record limit sits in Frappe's permission layer (`for_user`), and the two places Frappe does not cover are bounded by explicit terms with executed tests behind them |
| **Purpose limitation** | DPDP, same entry, 24 Aug 2026 | Yes | **Met.** Read state is still the recipient's only. No read-receipt surface was added — verified against the whole diff |
| **Data minimisation** | DPDP, same entry | Yes | **Met** for this slice: no new field, no new store, no new copy, no new export, no new address. One pre-existing gap found and routed (§3, P4-4) |
| **Breach intimation; CERT-In 6-hour clock** | DPDP; CERT-In Directions 28 Apr 2022, baseline §3, 24 Aug 2026; counsel 1 Nov 2026 (ALV-249) | Only if a control fails | Nothing new to log. The write is the clock-starting risk and it is tested three ways |
| **Performance records: employment + 6 months, then permanent erasure** | **Counsel, 18 Sep 2026**, binding | Yes, pre-existing | **Not met, and accepted in writing.** `Notification Log` rows are never deleted. R1, accepted by Surbhi 6 Nov 2026, **this slice only** |
| **Passport and health data are not for managers** | **Counsel, 1 Nov 2026** (ALV-249) | Yes | **Met.** None reaches any row — proved by the exact per-part key-set assertion, not by a promise |
| **EU AI Act** | baseline §4, 24 Aug 2026 | **No surface.** No model, no prompt, no automated decision, no profiling | n/a |

**I have asked counsel nothing.** Counsel has already ruled on retention (18 Sep) and on
manager access and breach handling (1 Nov). The only genuinely new question remains the
announcement read-receipt one, it is out of scope, it blocks nothing, and it is recorded
in `01c` §7 for Surbhi to route if she ever wants that feature.

**Housekeeping on the file I own:** the DPDP and CERT-In entries go stale on **22
November 2026**. R7.

---

## 10 · What I could not verify, and what I would need

1. **The `Cache-Control` header on the signed-in page, observed.** Still an inference
   from `frappe/app.py`'s `setdefault`, not an observation. *What I would need:* a
   browser session, or the CI assertion F-1 asks for.
2. **Chrome Android's bfcache on Back after logout.** A real handset. R5.
3. **Whether a real `DocShare` on a `Notification Log` row renders in a colleague's
   single-document door.** Mechanism proved in source; the row was never created,
   because creating it is a write.
4. **The mutation test for SEC-1.** I reasoned it out from the code and both tests
   rather than editing product code on a shared bench. §2.
5. **Anything at DTC beyond the authorised read-only counts.** I probed no tenant.
6. **Nothing was seen in a browser.** No screen in this slice has been looked at by me,
   and four things have been looked at by nobody (G-5).

**What I changed anywhere: nothing.** My checks were `git grep`, reading files, reading
Frappe's source inside `a83-bench`, and three read-only Python scripts against
`a83-bench`'s `test_site` that ended in `frappe.db.rollback()`. No `bench migrate`, no
cache clear, no site config change, no record written, nothing against `hrlocal-bench`,
dev or production.

---

## 11 · Subtract pass

I read this review again asking only what I could delete. **Removed:**

- **A new requirement for an audit entry on the bulk clear.** `update_modified=False`
  means nothing records when a bulk clear happened (G-10). I was going to ask for a
  timestamp. **Dropped:** no decision turns on it, there is no audit ledger to put it in
  (feature map A2, unbuilt), and adding a field and a per-row statement to get it would
  cost the one-statement property the slice was built for. The engineer named the cost
  and accepted it in the spec; that is the right shape.
- **A `Custom DocPerm` removing `share` and `export` from role `All`.** Tempting again,
  rejected again, for the same reason as 6 November, now with DTC's User Permission rows
  as extra evidence that the list door is shut. R3 stays.
- **A fifth privacy requirement on the revived `get_nav_counts`.** I read it instead. It
  returns counts only. A requirement would have been padding over a thing I had already
  checked.
- **An entry in `docs/security/questionnaire-answers.md`.** I said in `01c` I would fold
  the door table in at review. The file does not exist, and creating a new document to
  hold a table that already lives in `01c` §2 and now in AC-55 — which is executable —
  is a worse answer than the test. **The test is the questionnaire answer.** If a
  customer asks, the reply is `TestTheDoorsToSomebodyElsesNotices`.
- **A `threat-model-notifications.md` in `docs/security/`.** This feature is one slice.
  `01c` §1 is four lines and they are still true.
- **Three findings I had written as findings and demoted to worries**, because I could
  not write *this actor, calling this path, sees this data* for any of them.

**Result: 2 partials, 1 P3, 6 P4s, 2 worries, no new document, no new DocType, no new
permission layer, no new CI gate, no feature flag, and no new requirement.**

---

## 12 · Residual risk

| # | Risk | Severity | Owner | Status |
|---|---|---|---|---|
| **R1** | `Notification Log` rows are never deleted, including grooming-mark notices that counsel classes as performance records | temporary debt | Surbhi / `hrms-product-manager` | **Accepted in writing by Surbhi, 6 Nov 2026, for slice 083 only.** Not a standing waiver. Purge engine (A6) unbuilt |
| **R2** | An employee can CSV-export their own notice bodies from the Desk, including `email_content`, and have it emailed to their own address | acceptable simplification — own data, own address | me | Accepted 6 Nov 2026. AC-55 now proves it is **only** their own |
| **R3** | Role `All` holds `share` on `Notification Log`; a `DocShare` overrides our `has_permission` hook for the single-document door, so a person can disclose their own notice row | intentional trade-off, P4 | me | Accepted 6 Nov 2026, **reaffirmed 12 Nov** with DTC's User Permission rows as new evidence that the list door is shut. Reversible with one `Custom DocPerm` |
| **R4** | `inbox_api.py` has one `ignore_permissions` and no CI ceiling | security debt, P4 | me | Open, routed, not this slice's file |
| **R5** | **Chrome Android bfcache on a `no-store` page is unproven.** If Back after sign-out restores the page, the next holder of a shared handset sees the previous holder's 30 days of HR messages | **dangerous until the check is done** | `hrms-test-automation-engineer`; **Surbhi** if it fails | **Open. Release gate.** Fallback: one line on `pagehide` |
| **R6** | No tenant had been counted | — | — | **Closed, 11 Nov 2026**, by the authorised read-only count in `08-dtc-counts.md` |
| **R7** | Baseline DPDP and CERT-In entries go stale **22 Nov 2026** | security debt | me | Open, dated |
| **R8** · new | **SEC-6's header and redirect have no CI assertion** (F-1). The control is present today; nothing keeps it present | temporary debt, P2 | `hrms-test-automation-engineer` | **Open. Needs a fix or Surbhi's written acceptance with a date** |
| **R9** · new | **The notices half of this page is unobservable at DTC** — zero rows of all three kinds. A clean run at DTC proves nothing about notices | acceptable, but must be said to DTC | `hrms-product-manager` | Open. Also G-14's neighbour: tell DTC before they find an empty half |

**Accepted by:** nobody but Surbhi can accept R8 or close R5. Everything marked
"accepted by me" is reversible and has a date.

---

## 13 · What would have to change for me to call this a Blocker

I am recording this so the bar is visible and so nobody has to guess what I would stop
the line for:

- the bulk write losing either filter term, or gaining an argument;
- the count losing `for_user`;
- any `ignore_permissions` in `notices.py`;
- the service worker gaining a `respondWith`;
- `context.no_cache` being removed from `www/hrms_employee.py`;
- a read-receipt surface — per-recipient `read` state reaching anyone but the recipient;
- the Android check coming back showing rows, with no `pagehide` fix.

**None of those is true at `45e9b1c7`.**

---

**Written by `hrms-security-privacy-engineer`, 12 November 2026. I wrote `01c` and I
wrote AC-55, so `hrms-technofunctional-reviewer` should take the `mark_all_seen` move
and that test rather than rely on me. I am not a lawyer; every point of law above is
counsel's own ruling, cited with its date. I recommend; Surbhi decides.**
