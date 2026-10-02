# Slice 057 (ALV-181) — senior architect review

**Verdict: SHIP WITH FIXES.** The three builds work and the 043 email intake is
unchanged. But two small code faults should be fixed before the push to dev: a WhatsApp
message Meta sends twice makes two leads, and a step's task is lost when its email
cannot be sent. Two more points need Surbhi's written decision. "Ship" here means
"ready to present for a push decision". It is not permission to push.

Reviewed 2 Oct 2026. Branch `slice/057-amata-crm-demo`, commits 090e9dd, 9ef2ffc,
dfecb3d, 142dab7, on top of `origin/dev` 24ffbf4. No merge commits. Nobody else's work is
in the branch.

**What I ran (proven).** On the slice's own container `hrlocal-057`, site `test057`
(Frappe v16.35.0, CRM v1.84.0, frappe_whatsapp master 08bc1f6):

| Module | Result |
|---|---|
| test_ai_leads_whatsapp_057 | 19 tests, OK |
| test_crm_step_tasks_057 | 12 tests, OK |
| test_crm_summary_057 | 7 tests, OK |
| test_ai_leads_043 / _site_043 / _research_043 | 38 / 20 / 19 tests, OK |
| test_whatsapp_feature_042 / test_crm_feature_040 | 29 (9 skipped) / 40 (7 skipped), OK |
| `scripts/check_app_integrity.py` | 676 checks, OK |
| Full `alvoraa_portal` suite | **did not finish** in 50 minutes (my time limit). 3 failures in `test_review_outside_010d.TestR9LockReminder`; that module passes on its own (28 tests, OK). See §8 |

I also ran two small scripts on `test057` to prove findings 1 and 2 (both cleaned up or
rolled back). I touched no server, no other session's site, and no source file.

**Process gaps (proven by reading the folder).** There is no `01c` security file, no
functional spec, no implementation notes and no test report. The brief still says
"draft". `03-impact-and-strategy.md` §8 lists five decisions for Surbhi, and none of her
answers is written down in the slice folder. I took the caller's word that 03 is the
approved spec. Decision 3 (third-party text goes to the AI provider) is a privacy
acceptance and **must** be on record before dev.

---

## 1. Blockers

None.

## 2. Majors

### M1 — A WhatsApp message Meta delivers twice makes two leads and two AI calls · P2

- **Where:** `ai_leads/whatsapp.py:105-116` (`claim`) and `:93`. The claim is keyed on
  `doc.name`, the WhatsApp Message row's own random name.
- **Scenario:** Meta delivers webhooks "at least once". It sends the same message again
  when our reply is slow or not 200. frappe_whatsapp inserts a **new** WhatsApp Message
  row each time. `message_id` is not unique there (proven: `whatsapp_message.json`,
  `message_id` has no `unique`). So the second row has a new name. The claim passes.
  The model is called again and a second lead is made. A captured signed request,
  replayed, does the same, because Meta's signature carries no timestamp.
- **Proof (ran it):** two rows with the same `message_id` `wamid.REVIEWDUP1`, `process()` on
  each → `[('Lead created', 'CRM-LEAD-2026-00269'), ('Lead created', 'CRM-LEAD-2026-00270')]`.
- **Why it is wrong:** 03 §3.4 promises "Claim row stops double leads when Meta resends"
  and "Unique claim per WhatsApp message id". The test
  `test_the_same_message_twice_makes_one_lead` runs the job twice on **one** row, so it
  passes whatever happens on a real resend. That is a hollow test (lesson 1).
- **Smallest fix:** claim on Meta's id. Write `msg.message_id` (the `wamid`) into the
  call log's unique `whatsapp_message` field instead of the row name, and read it back
  the same way. Add one test: two rows with one `message_id` → one lead, one model call.

### M2 — When a step's email cannot be queued, the task is lost too · P2

- **Where:** `crm_steps.py:34-43` and `:54-70`. One savepoint covers both the task
  insert and the email.
- **Scenario:** the site has no default outgoing Email Account, or the email fails for
  any other reason while it is being queued. `make_email` raises. The `except` rolls back
  to the savepoint, and that removes the task that was just inserted.
- **Proof (ran it, then rolled back):** on `test057` (no outgoing account), a Partner
  Onboarding lead with an email moved to Qualified → `tasks: []`, Error Log
  `OutgoingEmailError: Unable to send mail because of a missing email account`.
- **Why it is wrong:** the task is the part the brief says must never be cut. The email
  is optional. Demo set-up step 7 makes an SMTP account but does not say to make it the
  **default** outgoing one. If it is not, every step that has a template makes no task.
  The test suite hides this because `ensure_outgoing_account()` always makes one.
- **Smallest fix:** keep the task insert under the first savepoint. Put the email in its
  own savepoint and `try`, after the task. Add a test with no outgoing account: the task
  is made, the email error is logged.

### M3 — Importing leads creates tasks and sends template emails to every imported customer · P2 · decision needed

- **Where:** `crm_steps.py:23-27`. The hook runs on insert (`has_value_changed` is true for
  a new record), and nothing checks `frappe.flags.in_import`.
- **Scenario:** at go-live Amata imports its existing pipeline (Data Import, say 300 leads
  with Lead Type and a status such as "Case Studies Sent"). Each insert fires its step.
  300 tasks are made and, where the step has a template, 300 real emails are queued to
  real customers.
- **Why it is wrong:** sent emails cannot be called back. Nothing in 03 decided what an
  import should do.
- **Decision needed:** does an import start steps? **My recommendation:** no. Return early
  when `frappe.flags.in_import` is set (one line, one test). **Owner:** Surbhi (the rule),
  then `hrms-fullstack-engineer`. **Risk if it waits:** none for Monday's demo. It becomes
  real at the first import.

### M4 — Messages from unlisted numbers are stored, though the brief promised "store nothing" · P2 · written acceptance needed

- **What the brief said (§5.2 and §9):** "Not on the list: drop it, store nothing."
- **What happens (proven by reading frappe_whatsapp `utils/webhook.py`):** for **every**
  incoming POST, frappe_whatsapp first writes the whole raw payload to **WhatsApp
  Notification Log**. That includes the sender's number, profile name and text. It then
  writes a **WhatsApp Message**. It does this for every sender, and for unsigned (forged)
  posts too, because the signature is only checked later, in our hook. Nothing deletes
  these rows. The test `test_no_or_a_wrong_signature_does_nothing` says so plainly
  ("frappe_whatsapp still stores it, as before").
- **Why it matters:** 03 §3.4 changed the brief's privacy promise to "non-listed numbers
  are untouched" and did not flag the change. This slice is what switches the webhook on
  for Amata. From then on, any Guest can add rows, and anyone who messages the number has
  their messages kept with no retention period. Only System Manager can read the two
  tables (proven), so this is **not** a leak to other users.
- **Decision needed:** accept this for the demo in writing, and open a YouTrack ticket for
  a retention period on WhatsApp Message and Notification Log rows. **My recommendation:**
  accept it for the demo. Do not delete upstream rows in our hook, because that would break
  frappe_whatsapp's own chat. Correct the brief's line. **Owner:** Surbhi, then
  `hrms-security-privacy-engineer` for the retention period.

## 3. Minors (P3: ship, write them down with an owner)

1. **A step task's person may not be able to open the lead.** Proven in CRM
   `permissions/org_hierarchy.py`. A Sales User sees only leads they own or are assigned
   to (a ToDo). So Nitin gets "Schedule site visit" for Vinda's lead, and opening the lead
   gives him a permission error. The set-up guide says this honestly (Part 4). In the demo,
   do not click through to the lead while logged in as Nitin or Sameeksha. A real fix means
   assigning the lead to the task's person, which widens who can see it. That is
   Surbhi's call, not a code fix.
2. **AI-made leads have no Lead Type, so moving them starts no step.** The brief's WOW
   shows the forwarded lead "tagged Client project". The build needs a person to set the
   type first. The demo plan covers this (row 6 note, rehearsal step 3). Only the brief's
   wording is out of date.
3. **Two steps with the same title on one status: the second never fires.**
   `crm_steps.py:47-53` checks for an open task by title only. "Site visit" for Nitin and
   "Site visit" for Sameeksha → only the first is made, silently. Fix: add `assigned_to` to
   the check, or tell admins to use different titles.
4. **"Deals won" counts a deal on two days.** `crm_summary.py:166-168`: `closed_date` is a
   Date (proven in `crm_deal.json`). The filter is `>= yesterday`, so a deal closed today
   before 09:00 is counted today and again tomorrow. Fix: `closed_date == yesterday`, or
   label it "yesterday and today".
5. **A WhatsApp job that crashes ends as Failed, with no lead and no retry.**
   `whatsapp.py:98-102`. Only the call log shows it, and nobody is alerted. The engineer
   declared this as temporary debt. Write it down with an owner.
6. **No AI check on WhatsApp-style text.** The 043 prompt calls the text "the email". The
   brief tells Amata that the AI reads Hindi. No test or evaluation feeds it a short,
   informal or Hindi forward. Rehearsal step 2 is the only check. Run three or four
   real-looking forwards, including one in Hindi, before Monday.

<details><summary>Nits (P4)</summary>

- `whatsapp.py:72`: `hmac.compare_digest` on two `str` values raises `TypeError` if the
  header holds a non-ASCII character. Only that forged request fails, with a 500. Comparing
  bytes (`.encode()` on both) avoids it.
- `whatsapp.py:25`: `cint` is imported and not used.
</details>

---

## 4. Acceptance check (from 03, the spec)

| # | Requirement | Result | Evidence |
|---|---|---|---|
| A1 | Matching step makes one task, right person, right due date | met | test `..._one_task_for_the_right_person`, passed |
| A2 | Other lead type / no type / save without status change → nothing | met | three tests, passed; `crm_steps.py:26` |
| A3 | Back and forth → no second open task | met (see Minor 3) | test, passed |
| A4 | Deal path | met | test, passed |
| A5 | Template email to the lead, shown on the timeline | met when a default outgoing account exists | test, passed; **M2** |
| A6 | Lead without email still gets its task | met | test, passed |
| A7 | A broken step never blocks the status change | met for the status; **partial** for the task | test passed; **M2** |
| A8 | Wrong status / type / disabled user refused on save; Sales User cannot write steps | met | tests, passed |
| B1 | Unlisted number → nothing, no row | met for "no lead, no AI"; the message is still stored | test passed; **M4** |
| B2 | Missing or wrong signature, or no secret → nothing | met, fails closed | tests through frappe_whatsapp's `post()` with a real werkzeug request |
| B3 | Sure → New lead owned by the forwarder, note, message linked | met | test, passed |
| B4 | Unsure → Needs Review; not a lead → none; AI down → Needs Review | met | tests, passed |
| B5 | Same message twice → one lead | **partial** | met for one row; **not met for a Meta resend (M1)** |
| B6 | Prompt has no forwarder number or name; PAN blanked | met | `test_the_model_never_sees_the_forwarder` |
| B7 | Known email/phone → existing lead; forwarder's number dropped | met | tests, passed |
| B8 | Shared cap; kill switch; email retry skips WhatsApp rows | met | tests, passed; the retry test would fail without the filter (read) |
| C1 | Off by default, no query | met | test, passed; `crm_summary.py:101-106` |
| C2 | Counts by type/step, overdue, won, full link | met (see Minor 4) | test, passed |
| C3 | No customer detail, no line break in variables | met | privacy-pin test, passed |
| C4 | WhatsApp failure still sends the email | met | test, passed |

## 5. NFR check

| Budget / dimension | 03 said | What the code does | Result |
|---|---|---|---|
| Performance — hook on CRM Lead/Deal | neutral, no query unless the status changed | Proven by reading `crm_steps.py:25-27`: two in-memory checks, then one query plus one exists-check and one insert per matching step | pass |
| Performance — webhook (Meta wants a fast reply) | site-config read for unlisted numbers | Proven: listed numbers add one meta read, one doc read, one password read and an HMAC. The model call is in a job | pass |
| Queries per request flat with volume | — | Summary: eight grouped queries whatever the volume (read) | pass |
| Security | improves vs. switching frappe_whatsapp on | Signature fails closed (proven by tests). Uses the raw body: Frappe caches `get_data()` (`frappe/app.py:364`) so the bytes match. Constant-time compare. No secret in any log. **But** dedup is by row, not Meta id (M1) | pass with M1 |
| Reliability | improves; errors never block a save | True for the save. The task can be lost (M2). A crashed WhatsApp job leaves Failed with no lead (Minor 5) | **partial** |
| Scalability | neutral | Fine at demo size. An import fires every step (M3) | pass with M3 |
| Maintainability | neutral | Three short files, one DocType. 043 reused, not copied. Hooks merge cleanly into local `dev` (checked with `git merge-tree`) | pass |
| Data integrity | unique claim per message id | **Not as stated** — unique per row (M1). Migration: `whatsapp_message` is nullable with a unique index; `communication` keeps its unique index and becomes nullable. MariaDB allows many NULLs, and Frappe saves an empty Data field as NULL (proven on `test057`). Email rows on sargam.dev keep their values. The sweep's left-join on `communication` is safe with NULLs (read `intake.py:188`) | **degraded vs. the claim** |
| Compliance / privacy | B degrades slightly, needs acceptance | Same, plus M4: unlisted senders' messages are stored with no retention period. The acceptance is not recorded | **open** |
| Multi-tenant | site config per tenant | Proven: forwarders, summary recipients and the kill switch come from `frappe.conf`; the secret is per WhatsApp Account | pass |
| Scheduler safety | off when not set | Proven by test and read | pass |

## 5b. Compliance and security check (no 01c exists, so these come from 03 and the baseline)

| Obligation | Mechanism in the diff | Test | Status |
|---|---|---|---|
| Forged webhook cannot spend AI money or make a lead | HMAC-SHA256 on the raw body, constant-time, fails closed | 3 webhook tests | discharged |
| Replay or Meta resend cannot make a second lead | unique claim on the row name | hollow (one row) | **not discharged (M1)** |
| Only listed forwarders reach the AI | site-config allow-list, checked in the hook and again in the job | test | discharged |
| Unlisted senders: nothing stored | none — frappe_whatsapp stores everything | test confirms storage | **not discharged (M4)**, needs acceptance |
| Forwarder's number and name never in the prompt | `for_model(SUBJECT, "", "", body)` | privacy-pin test | discharged |
| Identity numbers blanked | 043 `redact_ids` reused | test (PAN) | discharged |
| Untrusted text is data, not instruction | 043 markers reused; the model has no tools; code makes the lead and sets the status from fixed thresholds | 043 tests | discharged (structural, not only a prompt sentence) |
| Kill switch and cost cap | `ai_lead_intake_enabled`, empty list, shared daily cap | tests | discharged |
| No personal data or secret in logs | error logs carry record names only; `with_context=False` tracebacks; call log keeps no text | test (`no personal data in the log`) | discharged |
| Founders' summary sends counts only to Meta | fixed variables, clipped, no names | privacy-pin test | discharged |
| AI decision has a human reviewer | unsure → Needs Review list; owner = forwarder | tests | discharged |
| Third-party data sent to the AI provider (DPDP) | none in code; needs Surbhi's acceptance (03 §8 Q3) | — | **open — not recorded** |
| Task insert uses `ignore_permissions` | justified in a comment; the rows are manager-approved | Sales User cannot write steps (test) | discharged |

## 6. What to delete

Nothing. I checked each new piece by asking "what breaks if it is deleted?":

- The new DocType: frappe_whatsapp has no table an admin could fill. A child table on FCRM
  Settings would itself need a new DocType. It stays.
- The `alvoraa_app_secret` field: WhatsApp Account has no app-secret field (proven), and
  site config is not allowed for secrets (042 SEC-3). It stays.
- `switch_on_whatsapp`: it is the only checked way to set the forwarder list. It stays.

Only the unused `cint` import can go.

## 7. What was done well

- **The signature check was added even though frappe_whatsapp skips it.** It fails closed
  on every path: no request, no field, no secret, wrong header.
- **The tests go through frappe_whatsapp's real `post()` as Guest**, with a real werkzeug
  request. So the signature test checks the same bytes Meta signs.
- **043 was reused, not copied.** The only change to email intake is one filter, pinned
  by a test that would fail without it.
- **Counts only to Meta**, with a test that pins it.
- **The engineer said it honestly** that a step-task person may not be able to open the
  lead, and that AI-made leads need a type. They did not work around CRM's permission rule.

## 8. Confidence

- **Proven:** every finding above. I read the full diff, the reused 043 code, and the
  frappe_whatsapp and CRM source in the container. I ran the 057, 043, 042 and 040 test
  modules, two proof scripts, and the integrity check.
- **Full `alvoraa_portal` suite: not proven.** I started it on `test057` and stopped it after
  50 minutes, before the end. Up to then, 3 tests failed, all in
  `test_review_outside_010d.TestR9LockReminder` (the goals lock reminder). Run alone,
  that module passes (28 tests, OK). So it looks like those tests depend on which tests
  ran before them, not on 057, which does not touch goals **[inferred]**. **The full
  suite must run to the end once before the push to dev.** This slice adds hooks on
  CRM Lead, CRM Deal and WhatsApp Message and changes a shared DocType, so the 040
  and 042 modules alone are not enough. Allow 90 minutes or more.
- **Not checked:** the migration on a copy of sargam.dev's real data. I reasoned it from
  the schema and the column definitions only. Also not checked: real Meta delivery,
  template approval, and Gmail SMTP on amata.dev. Those need the tenant and Meta's
  dashboard.
- **frappe_whatsapp version (proven):** the container's copy reports 1.0.12, the same
  version as Amata. Its webhook stores the message inside Meta's request, so the
  signature check runs while the request is still open. Still send one signed forward on
  amata.dev during rehearsal. If the copy there stored messages in a background job, the
  check would fail closed and no forward would ever become a lead.

## 9. Before the push to dev

1. Fix M1 and M2 (small changes, one test each).
2. Surbhi decides M3, and gives written acceptance for M4 and for 03 §8 Q3.
3. Rebase onto `dev`, which now has 12 commits that are not on `origin/dev` (ALV-173,
   ALV-178, slice 058). Those also touch `hooks.py`. The merge is clean when tested with
   `git merge-tree`.
4. Pushing needs `bench migrate` on dev (a new DocType and a changed one).

Subtract pass: I removed a finding about `ai_lead_intake_enabled` being shared (it was
designed that way and is documented), a note on rule-name typos (validation already
catches them), and a Data Import performance worry (M3 covers the real risk).

## 10. Decisions and fixes after this review (2 Oct 2026)

- **M1 fixed** (326e1a9): the claim is keyed on Meta's message id. Test: two stored rows
  with one Meta id make one lead and one AI call.
- **M2 fixed** (326e1a9): task and email have their own savepoints. Test: a failed send
  leaves the task.
- **M4 and 03 §8 Q3 - accepted by Surbhi, her words, 2 Oct:** she accepts that
  frappe_whatsapp stores every incoming message (System Manager only) and that
  forwarded WhatsApp text goes to the AI provider, as email intake does. **Follow-up:**
  a retention period for WhatsApp Message and Notification Log rows (ticket filed by the
  coordinator).
- **Lead access:** step assignees are now also assigned the lead or deal (her option b),
  so a Sales User given a step task can open the record.
- **M3 approved and built (2 Oct):** a Data Import starts no steps; steps start on the next
  real status change. Test: `test_a_data_import_starts_no_steps`.
- Lead access test: `test_the_step_assignee_can_open_the_lead`. Side effect, from the CRM
  itself: the newest assignee becomes the Lead/Deal Owner; earlier owners keep access.
- Branch stays on `origin/dev` (her instruction): it is **not** rebased onto local `dev`.
