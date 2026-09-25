# Slice 043, slice one — implementation notes (local, 24 Sep 2026)

Scope: the pipeline only, no screens ("for the sake of this demo", the user, 24 Sep 2026;
spec §"Scope change"). Branch `slice/043-ai-email-leads`, worktree
`.claude/worktrees/043-ai-email-leads`, from `origin/dev` b06495d. Ticket ALV-121.

## 1. What was built

| File | What it does |
|---|---|
| `ai_leads/guards.py` | The mailbox rules V-1..V-7 as one pure `problems()` function; `validate_email_account` (Email Account validate hook), `validate_user` (User validate hook, the V-6 mirror), `account_still_ok` (V-7, run by the sweep before each mailbox) |
| `ai_leads/text.py` | Plain text only; quoted history cut; PAN, Aadhaar and card numbers blanked before sending; 6,000 characters; the model sees the sender's name and domain, never the address; the email cannot close its own marker |
| `ai_leads/rules.py` | Cheap skips before any paid call: machine senders, auto-replies and bounces, internal mail, the tenant's ignore list, HR and recruitment mail, newsletters, empty mail |
| `ai_leads/extract.py` | One call through the official `anthropic` SDK: `claude-haiku-4-5` by default (D-2), allow-list of three models, structured output with a closed JSON schema, no tools, versioned prompt `intake-v1` with the injection guard, 30 s timeout, 2 retries, refusal and truncation treated as failures, typed error chain mapped to short reasons that never contain the key. `clean()` re-checks every field: extra keys refused, links removed from name fields, phone kept only if its digits are in the email, website kept only if the email names it, identity numbers dropped. `decide()`: lead / review / not a lead, with a 0.70 floor |
| `ai_leads/intake.py` | The five-minute sweep (25 emails a run). Claims each email with a unique log row first; skips; attaches a known sender's email to their existing lead; makes an unread Needs Review lead when the daily cap is reached; otherwise calls the model and makes the lead in Frappe CRM's own form, with the email linked and the summary and reasons as a note. Failures retry; after three tries or 24 hours the email becomes a header-only Needs Review lead (SEC-26). Every lead and note is created by the service user `ai-leads@<site>`, never Administrator |
| `ai_leads/setup.py` | `switch_on(mailbox, daily_cap, owner)` and `switch_off()` for us to run on the server: custom fields, the "Needs Review" status, a public "Needs review" list in the CRM, the service user, the mailbox checks, the site-config switch and cap |
| doctype `Alvoraa AI Call Log` | One content-free row per email: outcome, short reason, lead, model, prompt version, confidence, tokens, attempts. Unique on the email, System Manager read-only, written only by the sweep |
| `hooks.py` | Email Account validate, User validate, cron `*/5 * * * *` |
| `subscription.py` | `ERPNEXT_FEATURES["crm_ai_intake"]`: "AI lead intake", opt-in, requires `crm`, in no plan. `requires_feature` now names ERPNext-side features by their label |
| `setup.py`, `requirements.txt` | `anthropic>=1.8,<2` (1.8.0 resolves on the image's Python 3.14; `pip check` clean) |

## 2. Proof

| Check | Result |
|---|---|
| `tests/test_ai_leads_043.py` — text, rules, schema, prompt guard, allow-list, the call against a fake SDK (request shape, no tools, refusal, error mapping, key never in errors), clean/decide, mailbox rules, the feature | **37 OK**, no database |
| `tests/test_ai_leads_site_043.py` — the whole pipeline on a real site with Frappe CRM, model stubbed: lead with email and note, same email twice, doubtful → Needs Review, invented phone, not an enquiry, machine mail, known sender, failure → retry → header-only lead, daily cap, switched off, default mailbox refused, HR user refused, an Employee cannot list the mailbox (AC-40) | **13 OK**, then **16 OK** after the review fixes (three new tests: a mailbox is still read after its oldest emails; an error after the claim ends as Failed; the sweep runs when on and does nothing when off; plus the public review list) |
| Neighbours: test_subscription 32, test_subscription_access 56, test_crm_feature_040 40, test_whatsapp_feature_042 29, test_access_control 34 | all OK |
| `scripts/check_app_integrity.py` | 635 checks, OK |
| `ruff check` on every new file | clean |
| Editable install of the app in the image pulls `anthropic` 1.8.0 | yes; no broken requirements |
| Whole `alvoraa_portal` suite | see §3 |

One fault found by the site tests and fixed in the code: with no config key, leads were created
as Administrator. The pipeline now falls back to the service user's fixed address.

**Not tested: a real model call.** Every test stubs the model; nothing has been sent to the API
and nothing has been paid for. A first live call needs an API key on the site and the user's word.

## 2b. Review (05-review.md) and what was fixed before commit

The reviewer ran on 24 Sep 2026 and blocked a push until two faults were fixed. Both are fixed,
with tests that fail without the fix:

| Finding | Fix |
|---|---|
| **P1-1** an email could stay "Queued" for ever if anything failed after the claim | every email runs inside `safely()`: roll back, finish as Failed with the error *type* only, move on; `retry_failed` also picks up Queued rows older than 15 minutes |
| **P1-2** a mailbox stopped being read once its oldest ~100 emails were handled | `unclaimed()` excludes claimed emails in the SQL itself (left join on the call log) |
| P2 over the daily cap every email became a junk lead | the claim is released and the sweep stops; the email waits for tomorrow (AC-30) |
| P2 the date filter used `creation` | `communication_date` - a first pull of old mail is not new |
| P2 the "Needs review" CRM view was invisible | `user = ""` on the public view |
| P2 `+919876543210` was blanked as an Aadhaar number | Aadhaar pattern skips numbers after "+" and 91 + mobile digit |
| P2 "Not a lead" stored the model's own words in the log | a fixed reason; the log stays content-free |
| P2 no time limit | a sweep stops after 240 s (the cron job's timeout is 300 s) |
| P2 the switched-off test passed whatever the code did | replaced by a test that runs `sweep()` off and on |
| P2 `retry_failed` counted rows it skipped and skipped the mailbox re-check | counts only what it worked on; re-checks each mailbox |

**Left for before a paying tenant** (review, unchanged): a breaker and alerts (SEC-20, OPS-12),
purge and erase (US-19/20), counsel and the DPA row (PRIV-11), the key in backups (OPS-9),
in-product acceptance of the data transfer (PRIV-1). All in ALV-122 / ALV-123.

## 3. Whole-suite result

`bench --site testwa042 run-tests --app alvoraa_portal` in the throwaway container, Frappe CRM
installed, this branch loaded: second block **1,040 OK, 16 skipped**. The first block had
**three failures, all guard tests doing their job**, all fixed and rerun green:

| Guard test | What it caught | Fix |
|---|---|---|
| test_portal_module_gate_016, no hardcoded addresses | test data on `.example.in` and bare `.example` domains | reserved `example.com` domains only |
| test_invoicing, every doctype classified | `Alvoraa AI Call Log` was neither tenant-side nor control-plane | added to `TENANT_DOCTYPES` |
| test_opt_in_features, only shipped opt-ins waiting | the `opt_in` flag made the feature show as "waiting" | flag dropped, as on `crm` and `whatsapp` (still off until ticked) |

Rerun after the fixes: test_portal_module_gate_016 17 OK, test_invoicing 24 OK,
test_opt_in_features 19 OK, test_ai_leads_043 37 OK, test_ai_leads_site_043 16 OK,
test_subscription 32 OK, test_crm_feature_040 40 OK, test_whatsapp_feature_042 29 OK.

## 4. To switch it on for the Sargam demo — each step on the user's word

1. Push to dev; the image picks up the SDK. Hand deploy from dev (main still lacks the ALV-112 step).
2. Tick "AI lead intake" for Sargam in the admin console (the tenant already has `crm`).
3. On the server, the user types the key herself:
   `docker exec -it devstack-backend-1 bash -c 'cd /home/frappe/frappe-bench; read -s -p "Key: " K; echo; bench --site sargam.dev.alvoraa.co set-config ai_lead_intake_api_key "$K"'`
4. The user creates the demo mailbox's Email Account (IMAP, incoming on, no Append To, CRM's own
   "create lead" off) and types its password herself.
5. We run `switch_on` with that mailbox, `daily_cap` 50 for the demo, owner `sales@sargam.dev.alvoraa.co`.
6. Send one real enquiry and one newsletter to the mailbox; within about ten minutes (mail pull,
   then the sweep) the enquiry is a lead and the newsletter is not.

## 5. Faster intake for the demo (25 Sep 2026)

The user: a demo cannot wait 15 minutes for a lead. The AI takes seconds; the wait was
two timers in a row - Frappe fetches mail every 10 minutes, the sweep ran every 5.

| Change | What it does |
|---|---|
| `intake.on_new_email` (Communication `after_insert`) | A newly fetched email on an intake mailbox is queued for the AI at once (`short` queue, after commit, one job per email). The model is never called inside the mail fetch |
| `intake.process_new` | That job: the sweep's own checks for one email (feature, mailbox rules V-7, the switch-on date, not already claimed), then the same `safely()` path |
| `intake.pull_intake_mailboxes`, cron every minute | Fetches intake mailboxes only, queued exactly as Frappe queues its own fetch (same queue, same job name), so the two never read one mailbox at once. Frappe's own fetch of other mailboxes stays at 10 minutes. No query on a site with intake off |
| The five-minute sweep | Unchanged; now the safety net and the retry |

Result: a lead about a minute after the email is sent, two at most.

Proof: `test_ai_leads_site_043` 20 OK (4 new: hand-over only for received mail on an intake
mailbox and only when on; one lead however many runs; mail from before switch-on ignored;
the one-minute fetch only when on, with Frappe's job name, never queued twice),
`test_ai_leads_043` 38 OK, integrity 636 OK, ruff clean.

Known limits, accepted for slice one: a burst of new mail becomes one job per email, so the
sweep's 25-per-run limit does not apply to it (the daily cap still does); an OAuth mailbox
without a token is fetched and fails in Frappe's own log, where Frappe's fetch would skip it
(no OAuth mailbox uses intake today).

## 6. Company details for sure leads (25 Sep 2026, approved the same day)

The user asked for the company's website, official address and published phone numbers
on each lead the AI is at least 85% sure of - "not deep research".

| Piece | What it does |
|---|---|
| `ai_leads/research.py` | Its own job after the lead is made. One model call with one web search: limited to the company's own site when its domain is known (from the website in the email, or the sender's address unless it is a public mail provider), else a search for the company name and city. Four fixed answer lines; code checks each (the website must be on the company's own domain, look-alikes refused; phones must look like phones; no markup or links in the address). A note "Company details (AI, please check)" on the lead; the website field filled only when empty; the person's phone never touched |
| What leaves the site | The company name, website and city from the lead. Never the person, the email address or the email text - the job reads the lead, not the email |
| Switch and limit | Off unless `ai_lead_intake_research` = 1 on the site; `ai_lead_intake_research_cap` a day, default 50 |
| Call log | New read-only fields: research (Done, Not found, Skipped, Failed), reason, searches, pages read, tokens |

Measured on real companies from the Sargam server, 25 Sep 2026:

| Way | Result | Cost |
|---|---|---|
| Read the website, two pages | a guessed contact page failed; only the website found | 1.8 cents |
| Read pages, then search the site | everything found, but a PDF and three pages read | 7.5 cents |
| One search, limited to the company's site (chosen) | website, phones, address where published | 2.1 cents each |

Proof: `test_ai_leads_research_043` 24 OK (17 no database, 7 on a site), `test_ai_leads_site_043`
20 OK, `test_ai_leads_043` 38 OK, test_invoicing 24 OK, test_subscription 32 OK; ruff clean;
integrity OK.
