---
slice: 043-ai-email-leads (slice one — pipeline only, no screens)
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-09-24
reviewed: worktree .claude/worktrees/043-ai-email-leads, branch slice/043-ai-email-leads, uncommitted, on top of b06495d
---

# 043 slice one — senior architect review

## 1. Verdict

**BLOCK for "push to dev and demo on Sargam", until two small fixes are in.** It is fine to commit locally now. Two faults mean an email can be silently lost for good:

- if anything goes wrong after the sweep takes ("claims") an email, that email is stuck forever;
- after about 100 emails, a mailbox is never read again.

Each fix is about 20 lines. The rest of the design is sound: extraction only, a closed schema, the sender taken from the header, and a content-free idempotency row (one log row per email, so a rerun cannot make a second lead). After the two P1 fixes it is fit for the demo. **"Ship" would never be permission to deploy.** Pushing to dev, and every server step, stays the user's call.

**What I could and could not run — read this first.**

| | |
|---|---|
| **Proven, ran it** | `tests/test_ai_leads_043.py` (no database): **37 OK**. I ran it in `hrlocal-wa042` with plain `python -m unittest`, not bench. The container's copies of all eight new files match the worktree byte for byte (md5 checked). |
| **Proven, read it** | The installed SDK there is `anthropic` 1.8.0, and `Messages.create` does accept `output_config`. CRM is 1.84.0 and Frappe is 16.35.0. I read CRM's `CRM Lead`, `CRM View Settings`, `CRM Lead Status` and `FCRM Note` definitions, and Frappe's `ScheduledJobType` and the queue timeouts. |
| **Not checked** | `tests/test_ai_leads_site_043.py` (13 tests on a real site). Running it needs bench and database writes, which this task does not allow. The "13 OK" in `03` is the engineer's claim, not mine. No real model call has been made by anyone. I also did not run the whole `alvoraa_portal` suite, and `03` §3 is still blank. |

## 2. Blockers (P1 — block the release)

### P1-1 · An email gets stuck at "Queued" forever if anything fails after it is claimed. Nothing reports it.

`ai_leads/intake.py:123-136` (`claim` commits), `:165-216` (`process_one`, no `try`), `:95-96` (any log row counts as done), `:102-104` (retry reads only `outcome = "Failed"`).

- **What happens.** `claim()` commits a log row with `Queued`. Then the job dies before `finish()` runs. Frappe's `ScheduledJobType.execute` catches the error, rolls back and moves on. Cron jobs have `create_log = 0`, so no Scheduled Job Log and no Error Log row is written.
- **Why it is stuck.** The log row stays `Queued`. `process_account` treats any log row as done, and `retry_failed` looks only at `Failed`. So the email is never read again, never becomes a lead, and nobody is told.
- **Things that trigger it — each one is real:**
  - (a) The default queue times out at 300 s (Frappe `background_jobs.py`: `"default": 300`). One sweep can run 25 emails × up to 3 × 30 s (`extract.py:93`: `timeout=30.0, max_retries=2`).
  - (b) The worker restarts while a sweep runs. This happens on every dev deploy.
  - (c) `CRM Lead.validate_email` calls `validate_email_address(..., throw=True)` and rejects an odd sender address.
  - (d) A database deadlock, or an `ImportError` if the SDK is missing from the image.
- **Why it is wrong.** It breaks the promise in the file's own header ("nothing is lost", SEC-26) and in spec §11 ("never zero"). The repo has already paid for this lesson once: see `tenant_api.py:151` and `:201` — "the console shows 'Queued' for ever".
- **Smallest fix, in two parts.**
  1. In `process_account` and `retry_failed`, wrap each `process_one` in `try/except Exception`. On an error: `frappe.db.rollback()`, then `finish(log, "Failed", reason=type(e).__name__, attempts=+1)`, then continue with the next email. Log only the exception class, never the message, because the message could hold email text.
  2. Make `retry_failed` also pick up `Queued` rows older than about 15 minutes.

### P1-2 · A mailbox is never read again once about 100 emails have come in since switch-on

`ai_leads/intake.py:80-96`.

- **What happens.** The query takes the **oldest** `limit × 4` Communications (at most 100) since `alvoraa_ai_since`. It drops the ones that already have a log row only after fetching them. Nothing ever moves `alvoraa_ai_since` forward: a grep finds only `guards.py:81` and `setup.py:127`, and both set it once.
- **The failure.** When the oldest 100 are all done, including skipped, linked and "not a lead" emails, `todo` is empty every time. New enquiries are never read. There is no error and no alert.
- **It can happen sooner.** When failed retries use up the batch budget (`budget = 25 − retries`), the window shrinks to `4 × budget`.
- **Why it is wrong.** The core outcome, "emails become leads", stops without a sound. At Sargam's estimate of about 40 emails a day, that is day three.
- **Smallest fix.** Leave out claimed emails in the query itself: a `frappe.qb` left join to `Alvoraa AI Call Log` where `log.name IS NULL`. Or move `alvoraa_ai_since` forward to the oldest unclaimed email after each run. Add a site test with 105 emails. Today `sweep()` and `process_account()` are never run with the feature on (see P2-7).

## 3. Majors (P2 — fix, or accept in writing before release)

1. **When the daily cap is reached, every further email becomes a lead, junk included.** `intake.py:192-194`.
   - What happens: once the cap is hit, each email that passes the cheap rules becomes an unread "Needs Review" lead. The batch allows 25 per 5 minutes, so up to 7,200 a day.
   - What the spec says: AC-30 says those emails *wait for the next day* and stay unlinked. E-21 caps even stale leads at 200 a day.
   - Result: one spam flood fills the CRM with junk leads.
   - Fix: when the cap is hit, `finish(log, "Cap reached")` without a lead, and let the next day's sweep take those rows oldest first.
2. **Old mail can be treated as new at switch-on.** `intake.py:87` filters on `creation`, which is when Frappe *pulled* the email, not when it was sent.
   - When it bites: if the mailbox's first pull runs after `switch_on` (steps 4 and 5 of `03` §4 done within 10 minutes of each other), Frappe's `initial_sync_count` of old emails all look new. They all go to the model, up to the cap, and then each becomes a cap lead (item 1).
   - Fix: also require `communication_date >= since`.
   - Label: Inferred from Frappe's pull behaviour. Not checked on a site.
3. **The "Needs review" list in the CRM is probably invisible to everyone.** `setup.py:82-93` never sets `user`, so the column is stored as NULL.
   - CRM's `crm/api/views.py:get_views` returns only rows where `user == ""` or `user == session user`. CRM's own `public()` sets `user = ""` explicitly for this reason.
   - Result: the saved filter the scope change promises would never appear.
   - Fix: `doc.user = ""`, plus `route_name = "Leads"`.
   - Label: Inferred from code. Not observed on a site.
4. **A common Indian mobile format is blanked as an Aadhaar number.** `text.py:27` (`_AADHAAR`).
   - Proven by running it: `+919876543210` becomes `+[ID number removed]`, and `919876543210` is blanked the same way. `0091 98765 43210` becomes `[card number removed]`.
   - Result: the model never sees the phone. If the model still returns it, `_clean_str` blanks it, the span check flags it, and the lead goes to review with no phone. That hurts the core "columns filled" promise for India.
   - Fix: do not treat 12 digits as Aadhaar when they are `91` followed by `[6-9]` and 9 more digits, or when they come right after a `+`.
5. **The call log is not content-free.** `intake.py:211-212` writes the model's first reason, word for word, into `reason` for "Not a lead". The model writes that sentence about the email, so it can hold a name, a price, or text an attacker planted.
   - Who can see it: System Manager only, who can already read every email. So no one new gains access (not a P0).
   - Why it still matters: it breaks SEC-17 and AC-35 ("no content"), and slice two's erase tool keeps log rows because "they hold no content" (AC-83).
   - Fix: store a fixed code such as `"not an enquiry"`. Keep the model's reasons only on a lead note.
6. **One sweep can hold the shared `default,short` worker past its 300 s timeout.**
   - Nothing stops it running long: there is no circuit breaker (SEC-20, AC-27, AC-29 — a switch that stops calls after repeated failures), no wall-time yield (spec §11: "≤ 5 min or it yields"), and the SDK retries inside the job.
   - During a provider outage, each sweep can take 300 s. Meanwhile the mail pull for every site on that bench waits (07 OPS-2, a fact there). This also triggers P1-1 (a).
   - Fix: `max_retries=0` (the next sweep is the retry), a time budget of about 120 s per sweep, and a simple breaker: after 3 `Failed` rows in a row, stop for this run.
7. **A test that passes whatever the code does — "hollow" — plus no end-to-end test of the sweep.** `tests/test_ai_leads_site_043.py:166-170`.
   - Why it is hollow: the "switched off" test would pass even with `enabled()` deleted. The test site does not name `crm_ai_intake` in `features`, so `sweep()` returns at `has_feature` before ever reaching `process_account` (Inferred from `subscription.enabled_features`).
   - What is never tested: no test runs `sweep()`, `process_account()` or `account_still_ok()` with the feature **on**. That is why P1-2 was not caught.
   - Fix: patch `has_feature` to True, then assert once with the switch off and once with it on.
8. **`retry_failed` counts rows it skipped, and skips the mailbox re-check.** `intake.py:109-111, 120`.
   - A `Failed` row whose mailbox was deleted or renamed hits `continue` every run and is never resolved. Yet it still uses up budget. With 25 such rows, intake stops for good.
   - Retries also skip V-7 (`account_still_ok`), so an email from a mailbox that is no longer allowed is still sent to the model.
   - Fix: count only rows actually processed; mark rows with no mailbox as `Skipped`; run `account_still_ok` before a retry.

## 4. Minors (P3 — can ship if written down with an owner)

1. **Billed failures do not count toward the cap.** A `Failed` call (non-JSON answer, `max_tokens` hit) is billed, but `called` stays 0 and tokens are 0 (`intake.py:200-201`). So those calls do not count toward the cap or the cost log.
2. **A short outage turns emails into unread leads for good.** Three tries at 5-minute gaps mean a 15-minute outage makes every email an unread header-only lead, with no later AI read. The header says "three tries **or** 24 hours"; the 24-hour path is effectively never reached.
3. **CRM's own update step is skipped when an email is linked.** `link_email` uses `frappe.db.set_value` (`intake.py:321-324`), so CRM's `on_communication_update` never runs. The lead's `communication_status` and `modified` are not updated, so the lead does not rise in the list.
4. **The stale fallback does not attach the email to an existing lead.** It records that lead (`intake.py:116`) but does not link the email to it and adds no note.
5. **One "From:" line can wipe the whole body.** `strip_quoted` cuts everything when the first line starts with `From:` (proven: an enquiry starting "From: Priya Mehta, Purchase" is sent as an empty body). The model then likely says "Not a lead", and the email is silently dropped.
6. **The end-marker check is case-sensitive.** `</email` defusing (`text.py:86-88`) lets `</EMAIL>` through. Low impact: the real guards are structural.
7. **Model text can pick the wrong industry or territory.** `_match` (`intake.py:221-224`) passes model text straight into a LIKE match, so `%` matches any record.
8. **Spec deviations nobody signed off.** Neither the scope-change table nor the Decisions table says these were dropped:
   - header rules (Auto-Submitted, List-Unsubscribe) replaced by subject and sender guesses — Frappe does not store the headers;
   - no Hindi HR words (AC-61);
   - a known sender's email is attached without enrichment (AC-21, AC-62);
   - no free-mail confidence cap (AC-10);
   - no notifications (US-13, AC-31);
   - no `latency_ms`, `cost_estimate` or `request_id` (AC-35, OPS-14);
   - `temperature` not set.

   Ask the BA to add them to the scope-change table, or to raise tickets.
9. **The impact analysis claims things the code does not have.** See §5. Fix `00`, or fix the code.
10. **A job on every site every 5 minutes, even where the feature is off.** Cost: one small job and one `last_execution` update per run. `create_log = 0`, so no log rows. Acceptable, but note it for DevOps.

P4: `03` §3 (whole-suite result) is still blank.

## 5. AC verification (slice one as re-scoped on 24 Sep)

| AC | State | Evidence |
|---|---|---|
| AC-6/7 lead with columns, email linked | met (stub) | site test `test_an_enquiry_becomes_a_lead_with_its_email`. Not run by me |
| AC-9 invented phone dropped → review | met | unit + site test. But see P2-4 for real Indian formats |
| AC-12/13 auto-reply / bulk skipped | partial | subject and sender guesses only (P3-8) |
| AC-14 internal / ignore list | met | `rules.py:53-62`, unit test |
| AC-15 not an enquiry → no lead | met | site test; the log reason leaks model text (P2-5) |
| AC-16 needs review | partial | status and flag met; no notification |
| AC-21/62 known sender | partial | attached, no enrichment, no phone-differs check |
| AC-24 no double lead | met for reruns | unique `communication` + `claim()`; overlapping runs are prevented by Frappe's `rq_job_id` dedupe (proven in `scheduled_job_type.py`) |
| AC-26/63 retry then fallback | partial | 15 minutes in practice, not 24 hours; P1-1 strands on a crash |
| AC-27/29 breaker | not met | not built (P2-6) |
| AC-30 cap: emails wait | not met | makes leads instead (P2-1) |
| AC-35 log content-free, with cost | partial | reason holds model text; no cost or latency |
| AC-40 Employee sees no mailbox emails | met (claimed) | site test; not run by me |
| AC-42/44 injection: header email, extra keys refused | met | `intake.py:259`, `extract.py:142-144`, unit tests |
| AC-47/51 kill switch | met in code, test hollow | `intake.py:53-54` read and correct; P2-7 |
| AC-49/50 feature opt-in, requires crm | met | unit tests |
| AC-56 no tools, closed schema, ≤ 6,000 chars, domain only | met | fake-SDK request-shape test; real SDK signature checked |
| AC-67–72 mailbox rules and User mirror | met in code; the hook wiring is tested only for Email Account | `test_the_sweep_is_scheduled...` asserts the Email Account hook; the User hook is called directly, not through `save()` |

## 6. NFR and the seven dimensions — impact analysis vs code

| Dimension | `00` claimed | Found in code |
|---|---|---|
| Performance | ≤ 12 queries per email, "asserted in a test" | No such test exists. The query count looks about right by reading (Inferred). |
| Security | `ignore_permissions` in 3 places, "counted by a test" | 5 places (log, lead, note, User, status/view in setup). No counting test. Each is justified. |
| Reliability | breaker, a defined end state on every path, never blocks the mail pull | **Degraded against the claim.** No breaker, the Queued dead end (P1-1), can block the shared worker (P2-6). |
| Scalability | the batch keeps a sweep to about 4 minutes | The 300 s timeout can be hit. The job runs on every site every 5 minutes (P3-10). |
| Maintainability | neutral | Agreed. Small, clear, Frappe-first modules. |
| Data integrity | one transaction per email; the cap count held in a locked row | The claim and the work are separate commits (by design), but there is no recovery path. The cap is counted on the fly with no lock. That is safe only because Frappe runs one sweep per site at a time. |
| Compliance / privacy | content-free log | Broken by P2-5. Retention and purge are slice two, and they **block a paying tenant**. |

§11 budgets: latency ≤ 15 min is **reasoned pass** for a trickle. Wall time "≤ 5 min or yield" **fails** (no yield). Cost is **not measured**, because no real call has been made.

## 5b. Compliance (slice-one obligations)

| Obligation | Mechanism | Test | State |
|---|---|---|---|
| SEC-1 extraction only, no tools | `extract.py:95-101` | `test_request_is_extraction_only` | discharged |
| SEC-6 the model names no target | `intake.py:259`, closed schema | unit + site | discharged |
| SEC-10/PRIV-2 minimum text, domain only | `text.for_model` | unit | discharged; over-redacts phones (P2-4) |
| SEC-12/14 key from site config, client per call | `extract.py:87-93` | `test_no_key...`, error mapping | discharged |
| SEC-17 content-free log | doctype has no text fields | none greps the values | **partial** (P2-5) |
| SEC-19 ceiling | `daily_cap`, CEILING 500 | cap test | **partial**: failures not counted; leads beyond the cap (P2-1) |
| SEC-20 breaker/backoff | — | — | **not discharged** |
| SEC-21 kill switch | `intake.py:53-54`, `switch_off` | hollow (P2-7) | partial |
| SEC-26 nothing lost | fallback lead | retry test | **not discharged** while P1-1/P1-2 stand |
| SEC-8/V-1..7 mailbox rules | `guards.py` + two hooks | unit + 2 site tests | discharged |
| PRIV-1 transfer acceptance | off-system (ALV-123) | — | accepted for demo by the scope change |
| PRIV-5/6/7, PRIV-11 purge, erase, DPA | slice two | — | **blocks a paying tenant** |
| OPS-9 key in backups | — | — | open, blocks a paying tenant (07) |

## 7. What to delete

- `ALLOWED_MODELS` entries `claude-sonnet-5` and `claude-opus-5` (`extract.py:25`). D-2 says Haiku until measured, and nobody has checked those two names. One entry is enough until the measurement.
- `text.mask_sender` is not used in the pipeline (only in a test). Remove it, or use it.
- `__pycache__/` folders sit inside the untracked `ai_leads/` and doctype folder. Do not stage them.

## 8. What was done well

- **The sender's address always comes from the email header, never from the model.** With the closed schema, the `extra keys → refuse` rule and no tools, the injection guard is structural, not a sentence in the prompt.
- **One unique log row per email as the idempotency key.** Combined with Frappe's own one-job-per-site dedupe, a rerun cannot make two leads.
- **Mailbox rules enforced on the document (validate), not the screen.** So the desk, the REST API and imports all obey them, and the sweep re-checks them.
- **Feature checks ordered cheapest first.** On a site without the feature, the sweep returns on a config read with no query.
- **Pure, database-free modules for text, rules and checking the answer.** 37 tests in 0.07 s.

## 9. Confidence and open questions

- **Must know (holds the verdict):** none beyond the two P1s. They are proven by reading the code paths end to end, including Frappe's scheduler and queue timeout code.
- **Should know:** were the P3-8 spec items dropped on purpose? Owner: `hrms-business-analyst`. Until someone says, they are ranked P3.
- **Not checked:** the site tests, the whole suite, a real model call and its cost, and whether the "Needs review" view shows on a real site (P2-3). To check these I would need bench access on `hrlocal-wa042` and a stub key.
- **Before a paying tenant, beyond the P1s:** P2-1, P2-2, P2-5, P2-6, the breaker and alerts (SEC-20, OPS-12), purge and erase (US-19/20), the DPA and counsel (PRIV-11), key rotation (OPS-9), and in-product acceptance (PRIV-1).
