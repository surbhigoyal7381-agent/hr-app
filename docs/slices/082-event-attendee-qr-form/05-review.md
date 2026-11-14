# 05 - Senior architect review, slice 082 (public event form -> CRM Lead)

**Verdict: SHIP WITH FIXES.** I found no blocker in the code. But it is **not ready to push** until the
fix-round commit `43da6e4b` has a recorded green test run (OPS-44, a P1 gate). Two privacy gaps (P2)
need a small fix or your written acceptance.

`SHIP WITH FIXES` is advice for the deploy decision. It is never permission to deploy.

- Reviewed: `git diff 0b0cff7b..43da6e4b` (4 commits, all by this slice's engineer, 18 files). I read
  `event_form.py`, `www/event_form.py`, `www/event-form.html`, `field_app_limits.py` and the hooks in
  full. I read Frappe's `rate_limiter.py` and `web_form.py`, and CRM's `api/doc.py` and `api/todo.py`,
  inside `hrlocal-qr082` (read-only).
- `git fetch origin dev`: nothing new on `origin/dev` after `0b0cff7b`. Nobody else's work came in.
- **I could not run any test.** The brief said reading and git only. All test results below come from
  `03` and `04`. **No run of `43da6e4b` is recorded anywhere.**

## 1. Findings, worst first

| # | Rank | Finding |
|---|---|---|
| F1 | **P1 gate** (Major) | **The fix round is unproven.** `04` says Fail (D1, D2). `43da6e4b` changes the code and adds a hook on three CRM doctypes, but no run of it is written down. *State:* a push today → D1/D2 are fixed only on paper. **Fix:** the test engineer re-runs `test_event_form_082` (51) and `test_portal_security_010` on test082, and adds a dated follow-up to `04` (OPS-44). |
| F2 | **P2** (Major) | **Erasure leaves the attendee's name in a CRM Notification copy.** *Inputs:* an event lead is assigned to a Sales User (the normal CRM flow; the SEC-10 test does exactly this) → CRM writes a `CRM Notification` whose `notification_text` contains `lead_name` (`crm/api/todo.py` 84-114, proven). The Sales Manager erases the lead with CRM's "delete linked" → `remove_linked_doc_reference` unlinks and `frappe.delete_doc`s the notification (`crm/api/doc.py` 717, 737, 797, proven) → Frappe keeps a Deleted Document row of it, with the name in it (inferred: standard `delete_doc`). `forget_unlinked_record` is hooked only on FCRM Note, CRM Task and CRM Call Log, and it reads `reference_docname`. CRM Notification uses `reference_name` (`event_form.py` 372-386). *Why it is wrong:* PRIV-5 says "erasure removes the person". AC-47 is met only as worded (it lets the engineer list the types), not in intent. **Smallest fix:** register the same hook on `CRM Notification`; read `reference_docname or reference_name`; add an assignment to the D1 test. About 3 lines plus 1 hook line. |
| F3 | **P2** (Major; needs your written call) | **The same published form has two other public doors, and our checks are not on them (W3 / OPS-43).** Frappe's own page `/<route>` and CRM's `/crm-form/<route>` save through `web_form.accept` (`frappe/website/doctype/web_form/web_form.py` 741-830, proven by reading). That code writes **every** row on the form, hidden ones too. It does not apply our consent-required rule, our "close on Link or sensitive field" rule, or our event stamp, and it inserts with `ignore_permissions`. *Inputs:* the organiser adds an "Aadhaar" question → our page closes, but `/<route>` still takes it. Or anyone drops `event-form/` from the poster URL → the lead saves with no consent tick and no `custom_event_form` → the erasure hook and the saved views never see it. Guest rate limit there: 10 a minute per address. *Why it is wrong:* these are privacy controls (priority rung 2) that live only in our page code. `data-doors.md` says that is not a limit. `01c` W3 and `07` OPS-43 record it, but it is **not** in your list of decided items. **I did not reproduce it with a POST**, because that would write a lead to a shared test site. **Options:** (a) accept in writing, as CRM as shipped (`06` owns the exposure); (b) a `CRM Lead` `before_insert` hook that refuses a Guest insert unless it came through our save. That is about 5 lines, but it switches off CRM's own form on every tenant, which is a product call. My advice: (a) for go-live, plus a line in the setup guide. Owner: `hrms-security-privacy-engineer`, then you. |
| F4 | P3 (Minor) | **The setup guide does not say to choose "delete linked".** `setup-guide.md` 148: "Delete their lead. Its history copies are removed with it." If the organiser picks CRM's "unlink" instead, the notes and tasks stay, text included. The hook leaves them alone on purpose (`event_form.py` 381). **Fix:** one sentence in the guide. |
| F5 | P3 (Minor, not checked) | **CI now installs CRM on `test_site` for the whole suite** (`ci.yml` +CRM_TAG, `install-app crm`). Tests that used to skip without CRM, such as slice 057's, will now run, and the bench cache key changes. No CI run of this is visible to me. Watch the first dev run. A red there may be a test that is newly running, not this slice. |
| F6 | P4 | Small things: (a) a CRM-side `ValidationError` on insert (for example two comma-separated emails, which pass `validate_email_address`) answers 500 "check your signal". Retrying will not help, and an Error Log row is written for a typo. (b) `_keep_expiry` has no try/except, unlike `_seconds_left`. (c) After the 30 s abort, the server may have saved, so a re-send can make a duplicate lead. |

**The two things you asked me to check**

- **`_limited` / `_keep_expiry`: behaviour unchanged for the 30 other uses (proven by reading).**
  - Frappe always creates the counter with `setex`, so it always has an expiry (`rate_limiter.py` 158-162). So `ttl == -1` happens only in the read-then-add race.
  - When there is no key (a GET, or no request), `ttl` is -2, so nothing happens.
  - The key matches Frappe's: `make_key("rl:cmd:id") + ":secs"` equals `make_key("rl:cmd:id:secs")`.
  - Cost: one extra Redis call per request.
  - Side effect: any counter on a live tenant that is already stuck with no expiry heals on its next call. That is an improvement.
  - The D2 test fails if `_keep_expiry` is removed. Good.
- **The erasure hooks are correct for CRM's delete path (traced).**
  - CRM unlinks each record with `doc.save()`, so `on_update` fires (`doc.py` 731-757), and then deletes it.
  - The `before_commit` callback finds the row gone and removes its copies.
  - A rollback resets the callbacks (`database.py` 1202), so a failed delete removes nothing.
  - With more than 10 leads, the lead delete runs in a background job, and the job's commit runs the same callback.
  - The only gap is F2.
- **`ignore_permissions` scope is tight (proven).**
  - There is one call (`event_form.py` 233), counted in CEILINGS at 1.
  - The document is built only from the open form's allowed rows plus the stamp. Any extra key refuses the whole save (228).
  - CRM's controller and Link checks still run.
  - Nothing else is skipped (no `ignore_mandatory`, no `ignore_links`).
- **Frappe-first:** no raw SQL. `frappe.db.delete` is the ORM call, used on a permitted delete only.

## 2. AC check (from 04 + my reading)

| ACs | Result | Evidence |
|---|---|---|
| AC-1,3-7,9-16,18-24,26-27,29-46,48-72,74-76 | Met | `04` §2, tests named there; I read the key ones (the AC-52 key refusal, the AC-58 crash log, the AC-25 window, PRIV-5) and each would fail if its feature broke |
| AC-25 (window ends), AC-47 (erasure) | **Partial: fixed in code, not re-run** (F1); AC-47 intent is partial (F2) | `test_082_ac25_a_window...`, `test_082_priv5_erasing..._the_crm_way` |
| AC-2, AC-8, AC-28 | Deferred to dev (your decision) | - |
| AC-17 / SEC-9 browser half, AC-72 TalkBack | Not run (needs a phone or browser) | `04` |
| AC-73 | Met by the script's self-test; it goes live only after `main` (OPS-37) | `check_event_refusals.sh --self-test` |

## 3. NFR check: before and after, against the impact analysis

| Dimension | 00 claimed | What the code shows |
|---|---|---|
| Performance | neutral; save p95 55 ms | Agree (inferred). Per save: 2 queries for the open check (meta is cached), CRM's insert, and 3-4 Redis calls. No N+1. `custom_event_form` has no index; that is fine at hundreds of leads per event |
| Security | degrades, bounded; Guest-row hook improves | Agree for our door. F3 is the unbounded part: the other doors are untouched by this slice and not closed by it |
| Reliability | improves | Agree. Rollback on failure, the answers stay on the page, a fixed 30 s timeout, and the counter can no longer get stuck (D2) |
| Scalability | 300/min per event | Agree. Keyed per event, so one full hall does not hold up another event (tested) |
| Maintainability | neutral | Fine. One module; `desk_request` reused under a desk name (written down in 03) |
| Data integrity | neutral | Agree. The callbacks are reset on rollback; `_keep_expiry` heals counters |
| Compliance / privacy | improves | **Partial.** Server-side consent, no personal data in logs or Redis (tested). Erasure misses CRM Notification (F2); the other doors skip consent (F3) |

## 4. Compliance

| Obligation | Mechanism | Test | Status |
|---|---|---|---|
| SEC-1 only the form's fields | Allow-list + whole-save refusal | AC-52 | Discharged (our door); F3 for the others |
| SEC-6 no Guest row | `Custom DocPerm` validate hook | AC-65, AC-66 | Discharged |
| PRIV-3 consent | Consent required on the server; ticks never pre-set | AC-57 | Discharged on our door; not on `/<route>` (F3) |
| PRIV-5 erasure | `after_delete` + unlink hooks | PRIV-5 tests | **Partial** (F1, F2) |
| PRIV-6 / OPS-28 no personal data in logs | Error Log holds hash + error type; log lines hold hash + reason | AC-58, AC-68 | Discharged |

## 5. What to delete

Nothing. Each part maps to an AC or to a decision you made. That includes the three entry points
for the five fields (install, migrate, CRM installed later), the two scripts (AC-67, AC-73) and the
DOM fixtures.

## 6. What was done well

- Keying the limit on the hashed event route, not the address. That is what makes a hall on one Wi-Fi work.
- One fixed reply body: no lead name and no echo of what was typed.
- An allow-list of field types, so a new Frappe type stays refused.
- The crash path logs only the hash and the error type, and a test feeds it a real-looking name and phone to prove it.
- The D2 fix is limited to keys with no expiry, so the other 30 limits stay the same.

## 7. Confidence

- **Proven by reading:** the limiter, the scope of the bypass, the erasure path, and F2 and F3 as code paths.
- **Inferred:** that F2's Deleted Document row is written, and that F3 saves end to end. I did not POST.
- **Not checked:** any test run (F1), the CI run with CRM installed (F5), the phone and browser checks.

**Subtract pass:** I dropped three suspicions I could not turn into a failure:

- a read-only row on the Web Form being drawn as editable;
- a `?route=` query on the page;
- the Error Log rollback by `desk_request` (AC-58 passes).

I removed nothing from the code list.

---

## Follow-up, 14 Nov 2026: fix round 2 (`git diff 43da6e4b..5059e179`)

**Verdict: SHIP WITH FIXES.** F2 and F4 are fixed in the code, and so is F6(b). I found no new
defect. The one thing that still holds the push is the same gate as before. `04` records a green
run of `43da6e4b`, which was fix round 1. **No run of `5059e179` is recorded** in `03` or `04`,
and I could not run one. F3 still needs your written call.

- Reviewed: 5 files, 1 commit, by this slice's engineer. Reading and git only. No containers.
- I checked the order of Frappe's delete steps in the local Frappe copy at
  `C:/Surbhi-Git/recruitment-AI-automation/frappe/model/delete_doc.py`. Its version may not match
  the image's v16.35.0, so anything that rests on that order is **inferred**.

| Check | Result |
|---|---|
| F2: CRM Notification copies | **Fixed (proven by reading).** `forget_unlinked_record` now reads `reference_name` for CRM Notification. The erasure test now assigns the lead, deletes as a Sales Manager, and asserts that no notice and no copy remain. |
| New `clear_lead_notices` (CRM Lead `on_trash`) | **Correct.** <br>1. *A lead with no event stamp:* the hook returns at once (`if not doc.get(EVENT_FORM)`). It reads the lead row being deleted, so it cannot touch another lead's notices. Both deletes are filtered on that one lead's name. **Proven.** <br>2. *A user without delete rights:* Frappe checks delete permission (`check_permission_and_not_submitted`, line 162) before `on_trash` runs (line 165). So nothing is deleted. **Inferred** (local Frappe copy). <br>3. *A delete that fails:* the link checks run after `on_trash` (lines 172-173), in the same transaction. A refusal rolls the notice deletes back, both in a desk request and in `delete_bulk`, which rolls back on any failure. **Inferred.** The one exception is a caller that catches the error and then commits. I found no such caller on the delete path. |
| Real bug found and fixed by the engineer | Before this fix, a Sales Manager could not erase an assigned event lead at all. CRM skipped the notice, Frappe then refused the lead, and CRM swallowed the error. The `on_trash` hook closes that gap for event leads only. |
| F4: the setup guide | **Fixed.** It now says to choose "Delete N items", not "Unlink & Delete". |
| F6(b): `_keep_expiry` | **Fixed.** It now has a try/except, the same as `_seconds_left`. The other limits behave as before. |
| `converted` and `facebook_lead_id` refused; "account number" and "religious" added | **Correct, and tested.** "account no" does not match "account number" ("no" vs "nu"), so the new word is needed. |

**New findings**

- **G1, P3. Mention notices can still leave a copy when a System Manager deletes the lead.**
  - *Scenario:* someone @mentions a colleague in a note on an event lead. That notice has
    `reference_doctype` = the note and `notification_type_doc` = the lead.
  - A System Manager can write that notice. So CRM's "delete linked" unlinks it and deletes it
    before the lead's own delete, and Frappe keeps a copy.
  - `forget_unlinked_record` skips it, because its `reference_doctype` before the save was not CRM
    Lead. The text may hold the person's name.
  - A Sales Manager is not affected: CRM skips the notice for them, and `clear_lead_notices` then
    removes it with no copy.
  - This is **inferred** from `crm/api/doc.py` 737-757. I did not run it.
  - Fix: also match on `notification_type_doctype` / `notification_type_doc`. That is 2 lines.
- **G2, P3. No test for the three edge cases.**
  - Missing: a lead with no event stamp keeps its notices; a delete by a user without delete
    rights removes nothing; a failed delete leaves its notices in place.
  - Right now the guard is proven only by reading.
  - Smallest useful test: assign a lead with no event stamp, try to delete it, and assert that its
    CRM Notification still exists.

**Subtract pass:** nothing to delete in round 2. Each change maps to F2, F4, F6 or a security-review
item.
