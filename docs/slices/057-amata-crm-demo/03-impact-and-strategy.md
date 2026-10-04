# Slice 057 — Amata CRM demo: impact analysis and strategy

Written Fri 2 Oct 2026 by the full-stack engineer. **Strategy only. No feature code is
written. Nothing is committed.** Surbhi approves, changes or rejects this before any build.

Demo: Mon 5 / Tue 6 Oct on `amata.dev.alvoraa.co`.

---

## 0. Read this first — five things that change the plan

1. **There is no brief, spec or security list for slice 057.** The normal process wants
   `01-product-brief.md`, `01c-security-privacy-requirements.md` and `02-functional-spec.md`
   before code. For a demo this weekend, Surbhi can choose to treat this document plus her
   own request as the spec. That is her decision, and it should be written down.
2. **Frappe CRM 1.84 has no stage automation and no per-type pipelines.** I read its source
   (tag v1.84.0). Lead statuses are one global list and deal statuses are another. Nothing
   creates a task when a status changes. So build A needs a little code.
3. **Meta's webhook is not signed-checked by frappe_whatsapp.** Anyone who learns the
   phone-number ID can post a fake "incoming message". Today that only adds a row to a list
   (slice 042 already noted it). Build B makes such a message spend AI money and create a
   lead, so **B checks Meta's signature itself and does nothing without it** (§3).
4. **A forwarded WhatsApp message does not carry the original sender.** WhatsApp only marks
   it "Forwarded". The original person's name, phone or email exist only if they are written
   in the text. When they are not, the lead is made as "Needs Review" with the text attached.
5. **A daily WhatsApp summary needs an approved Meta template.** Outside the 24-hour window
   (24 hours after the founder last wrote to the number), Meta delivers only approved
   templates. A plain text message is accepted by the API and then fails later. So the
   summary goes out as a template, and the email copy always goes too (§4).

**The local bench could not be read today.** Docker Desktop is not running, so
`hrlocal-bench` was not reachable. I read the CRM source from GitHub tag `v1.84.0` and
frappe_whatsapp from GitHub (it reports version 1.0.12, the same as Amata). Both must be
re-checked on the bench before the build starts.

---

## 1. Recommended order, effort and the Monday question

| Build | What it does | Rung | Effort (build + tests) | Monday? |
|---|---|---|---|---|
| A | Status change → CRM Task (+ optional email) per lead type | New DocType + one hook | 6 h | **Yes** |
| C | Daily summary to founders on WhatsApp (template) + email | New code (one file + cron) | 4 h | **Yes**, if Meta approves the template by Sunday; email copy works regardless |
| B | Forwarded WhatsApp → AI → CRM Lead | New code, reuses 043 | 8 h | **Possible, at risk** |
| — | Configuration and set-up guide | Configuration | 3 h | Yes |
| — | Review, full test run, fixes | — | 3 h | — |

**Total about 24 hours.** It can be built, tested and reviewed for Monday only if the
strategy is approved today and the work runs through the weekend in the order A → C → B.
Two things outside the code can still stop the demo:

- **Pushing to dev needs Surbhi's word, and a migration.** A adds a DocType, so dev needs
  `bench migrate`. The deploy pipeline also needs Actions minutes (the repo is private;
  ALV-164).
- **Meta set-up** (webhook, app secret, template approval) is done by Surbhi in Meta's
  dashboard and may take hours.

If time runs short, **drop B, not A or C.** The email intake from slice 043 already shows
"enquiry becomes lead by AI" for the demo story.

---

## 2. Build A — status change creates a task, per lead type

### 2.1 What already exists (checked in CRM 1.84 source)

| Thing | Does it do the job? |
|---|---|
| CRM status lists (`CRM Lead Status`, `CRM Deal Status`) | One global list each. No per-type list, no automation. |
| Frappe **Assignment Rule** (already 3 on Amata) | Assigns the lead itself to a user (a ToDo). It does not create a CRM Task, has no task title, and cannot set "due in N days". It also changes who the lead is assigned to, which is a different thing. **Rejected.** |
| Frappe **Notification** | Can email on status change, but cannot create a CRM Task. Would split one rule into two screens. **Rejected for the task part.** |
| **Server Script** | Needs server scripts switched on for the whole bench (a code-execution switch), is not under version control, and is not testable. Each step would be a script, which an admin cannot fill in like a table. **Rejected.** |
| CRM Task | Exists, with title, assignee, due date, link to lead/deal. On insert it assigns the user and CRM notifies them. **Used as is.** |
| Lead → Deal conversion | CRM copies every field with the same name from lead to deal (`get_deal_fieldname`). So a "Lead Type" custom field with the same name on both is carried over **with no code**. |

### 2.2 The honest answer to "one global status list"

CRM shows every status in the dropdown. Hiding statuses per lead type would mean changing
CRM's Vue screens, which is upstream code. I recommend:

- **Partner Onboarding runs on Lead statuses.** Add a few lead statuses, for example
  *Documents Received*, *Agreement Signed*, *Onboarded* (type Won).
- **Client Project runs on Deal statuses**, the standard ones (Qualification,
  Demo/Making, Proposal/Quotation, Negotiation, Ready to Close, Won, Lost).
- **The rule table is keyed by (Lead or Deal, lead type, status).** So a Partner lead moved
  to "Qualified" gets only the Partner tasks, and a Client lead gets only the Client tasks.
  The dropdown still shows all statuses; that is a stated limitation, not hidden.

### 2.3 The build (rung 5: one new DocType, because nothing cheaper holds an admin-filled table)

| Piece | Mechanism | Why |
|---|---|---|
| **Lead Type** field on CRM Lead and CRM Deal | **Configuration**: Customize Form, Select field, label "Lead Type" (fieldname `custom_lead_type`) on both. Added to CRM's Fields Layout so it shows in the CRM screens. | No code. Same fieldname on both, so conversion copies it. |
| **Alvoraa CRM Step Task** (new DocType, a plain list, not a child table) | Fields: *Applies to* (CRM Lead / CRM Deal), *Lead type* (Data), *Status* (Data), *Task title*, *Assign to* (Link User), *Due in days* (Int), *Email template* (Link Email Template, optional). Controller `validate`: the status exists in the right status list, the lead type is one of the field's options, the user is enabled. | An admin fills it in the desk like a table. One DocType, not a single + child pair. Status and type are Data, not Link, because a Link to a CRM DocType breaks `bench migrate` on tenants without CRM. |
| `alvoraa_portal/crm_steps.py` (about 40 lines) | `on_update` hook on CRM Lead and CRM Deal. Returns at once unless `doc.has_value_changed("status")` (no query). Then **one** query for matching rules. For each rule: skip if an open CRM Task with the same title already exists on that record; else insert a CRM Task (assignee, due = today + N days). If the rule has an email template and the record has an email, send it with Frappe's `communication.email.make` so it shows in the CRM email timeline. | `has_value_changed` is true on insert too, so a new lead at "New" gets its "New" tasks. |
| `hooks.py` | Two `doc_events` lines. Checked: alvoraa_portal has no existing "CRM Lead"/"CRM Deal" keys. | Hot file; additions only. |

**Error rule:** a broken rule must not stop a salesperson from changing a status. Rules are
checked when they are saved, so runtime errors are rare. If one still happens, it goes to
Frappe's Error Log with the record name only, and the status change goes through.

### 2.4 Impact

- **Cross-module:** CRM only (two hooks). No effect on `alvoraa_goals`, `hrms`, `erpnext`,
  payroll, leave or attendance. ERPNext's own CRM Deal `on_update` (create customer) is
  untouched and runs alongside.
- **Callers:** no existing function changes. New code only.
- **Personas:** *CXO / founders* — see tasks appear as deals move. *Sales Manager* — fills
  the rule table. *Sales user* (Vinda, Nitin, Sameeksha) — gets tasks in CRM's Tasks list and a
  CRM notification. *HR Manager, Employee* — nothing changes.
- **HRMS domain:** none.

| NFR | Verdict | Why |
|---|---|---|
| Performance | neutral | Zero queries when status did not change; one small query when it did; one insert per matching rule. |
| Security | neutral | Rule table: System Manager and Sales Manager write, Sales User read. Task insert uses `ignore_permissions` for that one insert only (it is a system action). |
| Reliability | improves | Duplicate-task check makes repeated moves safe. Errors logged, never block the save. |
| Scalability | neutral | Bounded by rules per status (a handful). |
| Maintainability | neutral | One small file, one DocType, readable rules. |
| Data integrity | neutral | Task created in the same transaction as the status save. |
| Compliance / privacy | neutral | Logs carry record names only. Email goes to the lead's own address, which is its purpose. |

**Tests** (`tests/test_crm_step_tasks_057.py`): matching rule makes one task with the right
user and due date; other lead type makes none; save without status change makes none;
moving back and forth makes no duplicate open task; deal path; template email goes to the
lead's address and appears on the timeline; lead without email gets the task, no email;
rule with an unknown status or disabled user is refused; a Sales User cannot create a rule.

---

## 3. Build B — forwarded WhatsApp message → AI → CRM Lead

### 3.1 What exists

- **Webhook URL Surbhi pastes into Meta:**
  `https://amata.dev.alvoraa.co/api/method/frappe_whatsapp.utils.webhook.webhook`
  with the **Verify token** = the value in the tenant's *WhatsApp Account → Webhook Verify
  Token*. Subscribe to the **messages** field. (Read in `frappe_whatsapp/utils/webhook.py`.)
- For a text message the app inserts a **WhatsApp Message**: `type` Incoming, `from` (the
  sender's number, digits only, e.g. `919812345678`), `message` (the text), `message_id`,
  `profile_name`, `whatsapp_account`. Forwarded status is not stored.
- CRM's own hook links an incoming WhatsApp message to any lead/deal/contact whose number
  matches `from`. **So the forwarder's number must never be put on the new lead**, or every
  later forward would attach to that lead.
- **No signature check** on the webhook POST (only the Flows endpoint checks one).

### 3.2 The build (rung 4: new code, reusing slice 043 nearly whole)

| Piece | What |
|---|---|
| Allow-list | **Site config** (per tenant, same as every other 043 setting): `ai_lead_whatsapp_forwarders` = `{"919800000001": "vinda@example.com", ...}`. Number → the CRM user who forwards. Empty or missing = off. No new switch. |
| `ai_leads/whatsapp.py` (new, about 120 lines) | `after_insert` hook on WhatsApp Message. Returns at once unless: incoming, text, `from` is on the list, intake is on (`ai_lead_intake_enabled`, feature `crm_ai_intake`), and **Meta's `X-Hub-Signature-256` matches the app secret** (checked here, while the webhook request is still open). Then queues one job, as 043 does for email. |
| The job | Claim a call-log row (one per message, unique — no double leads). Skip messages under 20 characters (a "hi" never reaches the AI). Shared daily cap with email. Build the prompt with 043's own `text.for_model` — subject "Forwarded WhatsApp message", **no sender name, no number**; the same redaction of PAN, Aadhaar and card numbers; same 6,000-character cut. Same model call, same field checks, same `decide()` thresholds. |
| Outcomes | **Sure lead** → CRM Lead, status New. **Unsure** → lead, status Needs Review (the same review list as email). **Sure not a lead** → no lead; the message stays in WhatsApp Messages. **AI fails** → Needs Review lead at once with the text attached (no retry loop; a WhatsApp message cannot be fetched again like a mailbox). |
| The lead | Name, company, job, phone from the AI (phone kept only if its digits are in the text). Email found by a plain pattern match in the text (no AI). Source "WhatsApp". **Owner = the forwarder's user.** A note says "Forwarded on WhatsApp by Vinda (+91 98…)" plus the AI summary. The WhatsApp message is linked to the lead, so it shows in the lead's WhatsApp tab. |
| Duplicates | If the email or phone found matches an existing lead, the message and a note go to that lead instead ("Lead updated"). |
| `Alvoraa AI Call Log` JSON | `communication` no longer required; add `whatsapp_message` (Data, unique). Data, not Link, so tenants without frappe_whatsapp still migrate. |
| `intake.retry_failed` | One filter added: only rows with a `communication`. Without it, a WhatsApp row marked Failed would be retried as an email with an empty mailbox name. |
| App secret | A Password custom field on WhatsApp Account (encrypted, never in site config — slice 042 SEC-3). Created by the set-up step only where WhatsApp is installed. |
| `hooks.py` | One `doc_events` line for WhatsApp Message. |

### 3.3 AI questions (as the agent rules require)

Objective: decide if a forwarded text is a sales enquiry and fill the lead columns.
Context: the forwarded text only (redacted, cut). Tools: none. Permissions: none — code
makes the lead. Boundaries: never sees the forwarder's number or name; never sends, replies
or changes a status. Confidence: same 0.85 / 0.85 / 0.70 floor as email. Human approval:
every unsure case is a Needs Review lead. Memory: nothing kept by the model. Audit: call-log
row with model, prompt version, tokens, outcome, no message text. Reversible: a wrong lead
is set to Junk. Failure: Needs Review lead; kill switch is the existing
`ai_lead_intake_enabled 0`, or an empty forwarders list.

### 3.4 Impact

- **Cross-module:** alvoraa_portal `ai_leads` (one filter in `intake.py`, one DocType JSON
  change), frappe_whatsapp (hook only, no upstream edit), CRM (lead creation, as 043).
  No HR modules.
- **Callers:** `retry_failed` is called only by `intake.sweep` (grep) and one test.
  `text.for_model`, `extract.*`, `rules` are reused without change. The call log's
  `communication` field is read in `intake.py` only (lines 147, 188, 221, 231–263); none
  of those reads break when WhatsApp rows have it empty.
- **Personas:** *Forwarders* (Vinda, Nitin, Sameeksha) — forward a chat, a lead appears with
  them as owner. *Sales Manager* — reviews unsure ones in the existing "Needs review" list.
  *Founders* — see it in the summary. *HR Manager, Employee* — nothing.

| NFR | Verdict | Why |
|---|---|---|
| Performance | neutral | The hook is a site-config read for any non-listed number. The model call runs in a background job, never in Meta's request (Meta expects a fast reply). |
| Security | **improves vs. just switching it on** | Signature check fails closed. Non-listed numbers are untouched. The model has no tools. Untrusted text stays inside the 043 markers. |
| Reliability | neutral | Claim row stops double leads when Meta resends. AI failure still gives a lead. A job killed mid-run leaves its row at Queued with no lead — **temporary debt**, rare, visible in the call log. |
| Scalability | neutral | Shared daily cap (200, ceiling 500). |
| Maintainability | neutral | One new file; 043's pieces reused, not copied. |
| Data integrity | neutral | Unique claim per WhatsApp message id. |
| Compliance / privacy | **degrades slightly — needs Surbhi's acceptance** | The forwarded text goes to the AI provider, as email bodies already do under 043. It may hold a third person's name and number, who never wrote to Amata. Mitigations: redaction, no forwarder details sent, no text in logs, only listed numbers. Amata's privacy notice should mention WhatsApp enquiries. |

**Tests** (`tests/test_ai_leads_whatsapp_057.py`, model mocked as in 043): non-listed number
→ nothing, no row; outgoing → nothing; missing or wrong signature → nothing; sure lead →
New lead, owner = forwarder, note names forwarder, message linked; unsure → Needs Review;
not a lead → no lead, row says so; model error → Needs Review lead; same message twice → one
lead; cap shared with email; **the prompt contains neither the forwarder's number nor
profile name** (privacy pin); PAN in text is blanked; known phone → existing lead updated;
kill switch off → nothing; a WhatsApp row marked Failed is not picked up by the email retry.

---

## 4. Build C — founders' summary

### 4.1 The Meta rule, plainly

- A business may send **free text** only within **24 hours** of the person's last message
  to it. After that, only an **approved message template** is delivered.
- A daily summary is almost always outside that window. So it must be a template.
- A template's variables cannot contain line breaks. So the layout lives in the template and
  each variable is one line, for example:
  > *Amata CRM, {{1}}.* New leads: {{2}}. By step: {{3}}. Overdue tasks: {{4}}. Deals won: {{5}}. Open the CRM: {{6}}
- **For the demo with Meta's test number:** the test number can send only to up to **5
  phone numbers verified in Meta's dashboard**, so the founders' numbers go there. Surbhi
  creates the template from the tenant's *WhatsApp Templates* screen today, category
  **Utility**; Meta usually approves within minutes to hours. If it is not approved by
  Sunday evening, the demo shows the email copy and explains the rule.
- A plain-text send outside the window does not fail at once; the API accepts it and the
  failure arrives later by webhook. So "send WhatsApp, fall back to email if it fails" cannot
  work reliably. **The email copy is always sent.**

### 4.2 The build (rung 4)

Rejected cheaper rungs: *Auto Email Report* sends one report per email and cannot combine
four counts or send WhatsApp; *WhatsApp Notification* (frappe_whatsapp) sends a template
per document, not one summary for many documents.

| Piece | What |
|---|---|
| `alvoraa_portal/crm_summary.py` (about 60 lines) | Six fixed queries whatever the volume: new leads by type; open leads by type and status; open deals by type and status; overdue CRM Tasks (not Done/Canceled, due before now); deals won in the period (count and total value). Builds the six one-line variables and the plain-text email. Links built with `frappe.utils.get_url("/crm/leads")` etc. Sends one WhatsApp Message per founder number (template + `body_param`, frappe_whatsapp's own send), and one email to the founder addresses. |
| Settings | Site config `crm_founder_summary` = `{"whatsapp": [...], "email": [...], "template": "..."}`. Missing = off, no query. |
| `hooks.py` | One cron line, daily at 09:00. For the demo, Surbhi presses **Execute** on the *Scheduled Job Type* in the desk to send it on the spot (no code). |

**Open question for Surbhi:** daily, or weekly (Monday 09:00)? I recommend daily for the
demo. If she wants both, I would make the period a site-config value, not a second job.

### 4.3 Impact

- **Cross-module:** CRM read-only; frappe_whatsapp send; Frappe email. No HR modules.
- **Personas:** *Founders* receive it. Everyone else: nothing.

| NFR | Verdict | Why |
|---|---|---|
| Performance | neutral | Six grouped queries once a day. |
| Security | neutral | Recipients only from site config, set by us. No endpoint added. |
| Reliability | neutral | WhatsApp error logged; email still sent. |
| Scalability | neutral | Fixed query count. |
| Maintainability | neutral | One file. |
| Data integrity | neutral | Read-only. |
| Compliance / privacy | neutral | **Counts only** go to Meta — no customer names, numbers or emails. Internal user names are not included either. |

**Tests** (`tests/test_crm_summary_057.py`): no config → returns with no query; counts by
type and step, overdue and won are right; no lead name, phone or email appears in the
WhatsApp variables (privacy pin); no variable contains a line break; a WhatsApp send error
still sends the email; links are full URLs.

---

## 5. Parallel-work check

| File | Others in it? | Plan |
|---|---|---|
| `alvoraa_portal/hooks.py` (hot) | Many slices over time; no open branch touches the CRM/WhatsApp keys (043, 040, 042 branches are fully merged into dev). | Add lines only; rebase on `origin/dev` right before commit. |
| `ai_leads/intake.py`, call-log DocType JSON | 043 is merged; no open branch changes them. | One filter, one field; pin tests. |
| New files (`crm_steps.py`, `ai_leads/whatsapp.py`, `crm_summary.py`, new DocType, tests) | None. | — |

`origin/dev` was fetched: nothing new beyond `24ffbf4`. The main checkout holds other
sessions' uncommitted files (agent docs, mobile app); none are in these paths. **Question
for Surbhi:** is any other developer working on CRM or WhatsApp this weekend?

---

## 6. Pure configuration for the demo (no code)

Done on `amata.dev.alvoraa.co` by Surbhi, or by us with her word (changing a dev tenant's
data is a dev-stage action).

1. **Users** Vinda, Nitin, Sameeksha (`@example.com`): role Sales User; **Send Welcome Email
   off**. Also turn off their email notifications (Notification Settings) — `example.com`
   never delivers, and every task assignment would bounce through Brevo and hurt the
   sending reputation. Check whether they count against Amata's plan seats.
2. **Lead Type**: Customize Form → CRM Lead and CRM Deal → Select "Lead Type", options
   *Client Project*, *Partner Onboarding*. Add it to CRM's Fields Layout (Quick Entry and
   Side Panel) for both.
3. **Statuses**: add lead statuses *Documents Received*, *Agreement Signed*, *Onboarded*
   (Won). Keep deal statuses as they are.
4. **Lead source** "WhatsApp" if it is not among the 14.
5. **Email templates** for two or three steps (e.g. Partner welcome pack, Proposal sent).
6. **Step-task rules** (after A is deployed): 6–8 rows covering both types.
7. **Email Account** `<demo Gmail inbox>`: IMAP and SMTP on, **Surbhi types the
   Gmail app password**; not default incoming; no "Append To"; CRM's "create lead from
   incoming email" off. Then AI intake is switched on with 043's `switch_on` (a server
   command — needs her word). Check `ai_lead_intake_api_key` is set on Amata.
8. **WhatsApp**: WhatsApp Account (token, phone number ID, business ID, app ID, verify
   token, **app secret**), set as default incoming and outgoing in WhatsApp Settings;
   webhook URL in Meta (§3.1); founders' and forwarders' numbers verified on the test number.
9. **Summary template** created in WhatsApp Templates (Utility) and approved.
10. **Sample leads**: about 8 across both types and steps, with email addresses Surbhi
    controls (step emails go to them). Two or three overdue tasks, one won deal.
11. Site config: `ai_lead_whatsapp_forwarders`, `crm_founder_summary` (server command —
    needs her word).

---

## 7. Set-up guide Surbhi can repeat (outline)

To be written as `docs/slices/057-amata-crm-demo/setup-guide.md` after the build, one
screen per step, each with "how to check it worked":

1. Before you start — what you need from Meta and Gmail, and the five-number limit.
2. Users without welcome emails, and their notification settings.
3. Lead Type field and CRM layout.
4. Statuses: which list holds which journey, and why.
5. Email templates, then step-task rules — with a test: move a lead, see the task.
6. The leads mailbox and AI intake — with a test email.
7. WhatsApp account, app secret, webhook, verify — with a test forward.
8. Forwarder list and founder summary settings — with "Execute" to send one now.
9. The summary template and the 24-hour rule.
10. Turning each part off (kill switches) and what to check if nothing happens
    (Error Log, AI Call Log, WhatsApp Notification Log).

---

## 8. Decisions waiting for Surbhi

1. Accept this document as the spec for a demo build (no separate brief/spec/01c)?
2. Approve rungs: A = one new DocType; B and C = new code. Order A → C → B; drop B if late?
3. B: accept that forwarded text (possibly a third person's details) goes to the AI provider,
   and that B needs the Meta app secret and does nothing without it?
4. C: daily or weekly? Template-only WhatsApp plus an email copy every time?
5. Is anyone else working on CRM or WhatsApp code this weekend?

## 9. Subtract pass

Removed while writing: a per-type status filter in CRM's dropdown (needs upstream Vue
change); a new "WhatsApp intake settings" screen (site config does it, like 043); a
"forwarded by" custom field on CRM Lead (owner + note record it); a retry loop for
WhatsApp AI failures (a review lead is enough); a WhatsApp-specific prompt version (043's
prompt is reused unchanged); a free-text summary path alongside the template (it fails
silently outside 24 hours); an "enabled" tick on step rules (delete the row instead).

## 10. Decisions recorded (Surbhi, 2 Oct 2026)

- **Approved** this document as the spec for the demo build; order A → C → B.
- **Privacy, accepted in her words:** she accepts that frappe_whatsapp stores every
  incoming WhatsApp message (readable by System Manager only), and that forwarded
  WhatsApp text is sent to the AI provider, the same as email intake.
- **Follow-up:** a retention period for WhatsApp Message and WhatsApp Notification Log
  rows. The coordinator files the YouTrack ticket.
- **Lead access for step assignees:** option (b) - the person given a step task is also
  assigned the lead or deal, the way the CRM assigns, so it shows in their list.
- **Founders' summary:** daily; goes to Vinda, Nitin, Sameeksha and Surbhi.
- **Settings page** (06): approved, to be built **after** the Monday demo.
- **M3** (import fires every step): approved - a Data Import starts no steps.
- **Tasks view:** a public "My open tasks" view in the CRM (no code), in the demo plan.

## 11. Added 4 Oct 2026 — instant refresh and the "Lead / Deal" column (ALV-181)

Approved by Surbhi on 4 Oct (option A plus the refresh fix). Rung: new code, in the
existing `crm_steps.py`, plus one Custom Field. Configuration alone could not do it:
the Tasks page can only show fields that exist on CRM Task.

- **Instant refresh.** After a step makes a task, `crm_steps._make_task` sends CRM's
  own `refetch_resource` event with the key `["activity", <lead or deal>]`, after
  commit, to the record's room. The lead page joins that room (Activities.vue,
  `doc_subscribe`, which checks permission), so everyone with the page open sees the
  task at once. Sent only when a task is actually made.
- **The column.** Custom Field `alvoraa_lead_deal` ("Lead / Deal", Data, read only,
  in list view, in standard filter) on CRM Task. Added by `after_migrate`
  (`crm_steps.ensure_task_label_field`, a no-op without CRM) and by the patch
  `crm_task_lead_deal_label`, which also fills existing tasks (page of 500, writes only
  rows that differ, so it is safe to run twice). A `validate` hook on CRM Task fills it
  on every task: one read of the lead or deal, only when the task is new or its
  reference changed. CRM's Columns button lists any visible field of the doctype's meta,
  so no CRM setting is needed; the CRM's default columns for tasks are fixed in its code,
  so each person (or a public view) adds the column once.
- **Privacy, for Surbhi to decide before the push.** CRM lets every Sales User read
  every CRM Task, but only their own (or assigned) leads and deals. Today the Tasks page
  shows another person's task with a lead *number*. With this column it shows that
  lead's **person and company** too. For a small team who all see all leads this changes
  nothing; where sales users must not see each other's leads, it does.
- **Review fixes, 4 Oct.**
  - The hook fills the column only if the person saving the task may open that lead or
    deal (`frappe.has_permission`). Before, anyone could point a task at a guessed lead
    number and read its person and company off the task.
  - A CRM Lead / CRM Deal `on_update` hook (`refresh_task_labels`) rewrites the column
    on that record's tasks when `lead_name`, `first_name`, `last_name` or `organization`
    changes, so a corrected or erased name does not linger. One update, and only then.
    `reference_docname` has no index; fine at today's volumes, measure before adding one.
  - `ensure_task_label_field` uses `update=False`, so a migrate never undoes a choice
    made in Customize Form (for example, hiding the column).
  - `after_app_install` adds the column the moment CRM is installed after our app.
  - The setup guide no longer promises a quick filter box: CRM's quick filters come
    from its own fixed list in CRM Global Settings. Use the Filter button.
- **Still open: the list itself (finding 1a).** Every Sales User can read every CRM
  Task, so the column shows the person and company of leads they cannot open, in the
  list and in exports. **Surbhi decides before the push:** accept it (small team, all
  see all leads), or hide the column (Customize Form, untick In List View — kept across
  deploys now), or ask for a CRM Task permission rule that copies the lead and deal
  rules (a larger change).
- **Known gap.** On a site where CRM was installed and tasks made before the field
  existed, those tasks are filled only if the patch runs after the field exists. The
  install hook above closes this for new installs; acceptable simplification.

