# Slice 057 — Set-up guide: steps that make tasks, WhatsApp leads and the founders' summary

Written 2 Oct 2026. For Surbhi, to set this up on any tenant by herself.
It assumes the tenant already runs Frappe CRM and Frappe WhatsApp, and that the code
from slice 057 has been deployed there.

Work through the parts in order. Each part ends with **Check it worked**.

Some steps are typed on the server (`bench ...`). Those are marked **Server**. Everything
else is done in the browser, as a System Manager.

---

## Part 0 — Before you start

Have these ready:

| What | Where you get it |
|---|---|
| A Gmail address for enquiries, and a Gmail **app password** for it | Google Account → Security → 2-Step Verification → App passwords. You type it in step 6; never paste it into a file or a chat. |
| Meta: a WhatsApp Business app with a phone number (the test number is fine for a demo) | developers.facebook.com → your app → WhatsApp → API Setup |
| From Meta: **access token, phone number ID, WhatsApp Business account ID, app ID** | Same page (API Setup). Use a permanent (system user) token for anything longer than a day. |
| From Meta: the **app secret** | App settings → Basic → App secret → Show |
| The phone numbers of the people who will forward leads, and of the founders | Ask them. Write each with the country code and no `+` or spaces, e.g. `919812345678`. |

**Meta's test number limit.** A test number can send messages only to **5 phone numbers**
that you have added and verified in Meta (API Setup → "To" → Manage phone number list).
Put the founders' numbers there. Forwarders do not need to be on that list to *send* to
the number.

**The AI key.** The tenant needs `ai_lead_intake_api_key` set (slice 043). Check:
**Server** `bench --site <site> show-config | grep ai_lead_intake_api_key` (it shows the
key is set; do not share the output). If it is missing, set it the 043 way — typed, not
pasted into a file.

**The feature.** In the admin console, the tenant must have **CRM** and **AI lead intake**
ticked. Without them, nothing in parts 6–7 runs.

---

## Part 1 — Users, with no welcome email and no notification emails

For each salesperson (for the demo: `vinda@example.com`, `nitin@example.com`,
`sameeksha@example.com`):

1. Desk → **User** → New. Email, first name.
2. **Untick "Send Welcome Email"** before saving.
3. Roles: **Sales User**. (Give **Sales Manager** to whoever will edit the step table.)
4. Save. Then set a password in the user form (Change Password) so they can log in.
5. Desk → **Notification Settings** → open the user's record → untick
   **Enable Email Notifications**. Save.

Why step 5: every task assignment and mention sends an email. `example.com` addresses
never receive mail, so each one bounces, and bounces hurt the tenant's sending reputation.
In-app CRM notifications still work.

Also check whether these users count against the tenant's plan seats.

**Check it worked:** log in as the user at `/crm`. No email arrives anywhere.

---

## Part 2 — The Lead Type field, on leads and on deals

1. Desk → **Customize Form** → Enter Form Type: **CRM Lead**.
2. Add a row: Label **Lead Type**, Type **Select**, Options (one per line):
   ```
   Client Project
   Partner Onboarding
   ```
   Put it just after **Status**. Save (**Update**).
3. Do exactly the same on **CRM Deal**: same label, same options.

The code looks for the field called `custom_lead_type`, which is what the label
"Lead Type" becomes. **Do not rename it.** Using the same name on lead and deal means the
CRM copies the type across when a lead is converted to a deal.

4. Show it in the CRM screens: `/crm` → your name (bottom left) → **Settings** →
   **Automation & Rules → Forms**. For **Lead**, open **Quick Entry** and **Side Panel**,
   add **Lead Type**, save. Do the same for **Deal**.

**Check it worked:** open a lead in `/crm`. The side panel shows Lead Type with the two
options.

Optional, same way: a **Solution Area** Select field on both (see the demo plan).

---

## Part 3 — Statuses: which list holds which journey

The CRM has **one** list of lead statuses and **one** list of deal statuses, shared by
every lead type. It cannot show different statuses per type. So:

- A **step** is "this lead type reaching this status". Two types can share a status and
  still get different tasks.
- The dropdown always shows every status. Tell users which ones belong to their journey.
- Statuses of type **Won** or **Lost** count as closed in the founders' summary. Note the
  CRM's standard **Qualified** lead status is type **Won**.

Add lead statuses: Desk → **CRM Lead Status** → New. Fill *Lead Status* (the name),
*Type* (Open / Ongoing / On Hold / Won / Lost), *Color*, *Position* (order in the list).
Deal statuses the same way in **CRM Deal Status**.

**Check it worked:** a lead's status dropdown in `/crm` shows the new statuses.

---

## Part 4 — Email templates, then the step table

**Email templates.** `/crm` → Settings → **Email → Templates** → New. Give it a name, a
subject and a body. You can use the lead's fields, for example `{{ first_name }}` or
`{{ organization }}`. Keep a template **Enabled**.

**The step table.** Desk → search **Alvoraa CRM Step Task** → New. One row per step:

| Field | What to put |
|---|---|
| Applies to | **CRM Lead** if the step is a lead status, **CRM Deal** if it is a deal status |
| Lead type | Exactly as in the field's options, e.g. `Client Project` |
| Status | The status name exactly as in the CRM, e.g. `Site Visit` |
| Task title | What the person must do, e.g. `Schedule site visit` |
| Assign to | The user who does it |
| Due in days | 0 = today, 2 = in two days. Due time is 6 pm. |
| Email template | Optional. Sent to the lead's own email when the step starts |

The row is checked when you save it: a misspelt status, a type that is not an option,
or a disabled user is refused with a message saying what to fix.

How it behaves:

- When a lead or deal **of that type** reaches **that status**, a CRM Task is created and
  assigned. The person sees it in **Tasks** and gets a CRM notification.
- A record that already has an open task with the same title does not get a second one
  (moving back and forth is safe). Once that task is Done, reaching the step again makes a
  new one.
- A lead with no Lead Type gets no tasks.
- If the record has no email address, the task is still made and no email goes.
- The email is sent as the person who changed the status, from the tenant's outgoing
  mailbox, and shows on the lead's Emails tab.
- If a step fails (for example its user was disabled later), the status change still goes
  through and the error is in **Error Log** ("CRM step ... failed on ...").

**Who can open what.** The CRM lets a **Sales User** open only the leads and deals they
own or are assigned to. So when a step makes a task, the person is **also assigned the
lead or deal**, the same way the CRM's own "Assign to" does. They see it in their lead
list and can open it. Note what the CRM then does: **the newest assignee becomes the Lead
Owner** (Deal Owner). Earlier owners keep access, because each has their own assignment.

**Imports.** Leads loaded with **Data Import** start no steps: no tasks, no emails. Steps
start the next time someone changes the status.

**Check it worked:** create a test lead with Lead Type set, move it to a status that has a
step. In `/crm` → **Tasks**, the task is there with the right person and due date. If the
step has a template and the lead an email address, the email is on the lead's Emails tab.

To stop a step: delete its row.

---

## Part 5 — The leads mailbox and AI email intake (slice 043)

1. Desk → **Email Account** → New.
   - Email address: `<demo Gmail inbox>` (for the demo)
   - Service: **GMail**
   - Password: **type the Gmail app password yourself**
   - **Enable Incoming**: on. Not the default incoming account. No "Append To".
   - Leave **Default Outgoing** off (the tenant's normal mailbox keeps sending).
2. In the CRM's own email settings, leave "create lead from incoming email" **off** — the
   AI intake does that job.
3. **Server**, switch intake on for this mailbox (use the Email Account's name):
   ```
   bench --site <site> execute alvoraa_portal.ai_leads.setup.switch_on \
     --kwargs "{'mailbox': '<Email Account name>', 'daily_cap': 200}"
   ```
   It refuses a mailbox that breaks a rule and says why.

**Check it worked:** send a short enquiry from another address to the mailbox. Within
about two minutes a lead appears in `/crm`, with an "AI summary" note. Desk →
**Alvoraa AI Call Log** shows one row for it.

---

## Part 6 — WhatsApp: the account, the app secret and Meta's webhook

1. Desk → **WhatsApp Account** → New:
   - Account name: anything, e.g. `Amata`
   - Token, URL `https://graph.facebook.com`, Version (e.g. `v20.0`),
     Phone ID, Business ID, App ID: from Meta
   - **Webhook Verify Token**: make up a long random word and note it
   - **Meta app secret**: type the app secret from Meta (it is stored encrypted and shown
     as dots afterwards)
   - Tick **Is Default Incoming** and **Is Default Outgoing**
   - Save.

   If the **Meta app secret** box is missing, run step 2 of Part 7 first, then come back.

2. In Meta: your app → WhatsApp → **Configuration** → Webhook → Edit:
   - Callback URL:
     `https://<tenant domain>/api/method/frappe_whatsapp.utils.webhook.webhook`
     (for the demo: `https://amata.dev.alvoraa.co/api/method/frappe_whatsapp.utils.webhook.webhook`)
   - Verify token: the same word as in step 1
   - Verify and save. Then **Subscribe** to the **messages** field.

**Without the app secret, no forwarded message ever becomes a lead.** The webhook is
public; the secret is how we know a message really came from Meta.

**Check it worked:** send any WhatsApp message to the business number. Desk →
**WhatsApp Message** shows it as Incoming within seconds.

---

## Part 7 — Forwarders: who may turn a forwarded message into a lead

1. Decide the list: each forwarder's WhatsApp number → their CRM user.
2. **Server**:
   ```
   bench --site <site> execute alvoraa_portal.ai_leads.setup.switch_on_whatsapp \
     --kwargs "{'forwarders': {'919800000001': 'vinda@example.com', '919800000002': 'nitin@example.com'}}"
   ```
   This adds the app-secret box to WhatsApp Account, the "Needs Review" status and list,
   the "WhatsApp" lead source, and the AI service user, and saves the list. It **replaces**
   the whole list each time. It refuses a number without a country code or a user who
   cannot log in. The answer says whether an app secret and an AI key are set.

How it behaves:

- Only text messages from listed numbers are read. Anything else stays in WhatsApp
  Messages as before, untouched.
- Messages under 20 characters are skipped ("hi", "ok").
- The AI sees only the forwarded words — never the forwarder's number or name. PAN,
  Aadhaar and card numbers are blanked first.
- Sure it is an enquiry → lead, status **New**. Unsure → lead, status **Needs Review**.
  Sure it is not → no lead. AI down or today's cap reached → **Needs Review** lead at once.
- The lead's **Lead Owner is the forwarder**. A note says who forwarded it. The message is
  on the lead's **WhatsApp** tab. The forwarder's own number is never put on the lead.
- If an email address or phone number in the message already belongs to a lead, the
  message is attached to that lead instead ("Lead updated").
- A forwarded lead arrives with **no Lead Type**: the salesperson sets it, then moves the
  status, and the step tasks follow.
- Email and WhatsApp share one daily AI cap (200 by default).

**Check it worked:** from a listed phone, forward a real-looking enquiry of a few lines to
the business number. Within a minute: a new lead, owner = that salesperson, with the AI
note. Then send the same from an unlisted phone: nothing happens. If nothing happens from
a listed phone, see Part 10.

---

## Part 8 — The founders' summary

### 8.1 The template (Meta must approve it)

Meta delivers a business-started message outside 24 hours of the person's last message
**only as an approved template**. A daily summary is always business-started, so it is a
template. Plain text would be accepted and then quietly fail.

`/app/whatsapp-templates` → New:

- Template name: `crm_daily_summary` (lower case, underscores)
- Category: **UTILITY**. Language: English. Account: the WhatsApp Account.
- Template (body), copied exactly — each `{{n}}` is one line of the summary, and a value
  can never contain a line break:
  ```
  Amata CRM summary for {{1}}.
  New leads in the last 24 hours: {{2}}.
  Open, by step: {{3}}.
  Overdue tasks: {{4}}.
  Deals won since yesterday: {{5}}.
  Open the CRM: {{6}}
  ```
- **Sample Values** — six, separated by commas, **no commas inside a value**:
  ```
  2 Oct 2026,3 (Client Project 2 and Partner Onboarding 1),Client Project: New 1 and Site Visit 2,1,1 worth Rs 2 lakh,https://amata.dev.alvoraa.co/crm/leads
  ```
  The sample values are required: without them the summary is sent with no numbers.
- Save. It is sent to Meta for approval. Approval usually takes minutes to a few hours.
  The **Status** field shows APPROVED when done.
- Note the record's **name** as the desk shows it (usually `crm_daily_summary-en`).

### 8.2 Recipients

**Server** (one line; empty lists turn it off):
```
bench --site <site> set-config --parse crm_founder_summary \
  '{"whatsapp": ["919800000001"], "email": ["founder@example.com"], "template": "crm_daily_summary-en"}'
```
The email copy **always** goes, even when WhatsApp works, because a WhatsApp failure is
only reported back later.

The summary holds **counts only** — no customer names, numbers or emails, and no staff
names.

### 8.3 When it runs, and sending one now

It runs every day at **09:00** site time. To send one now (for the demo):
Desk → **Scheduled Job Type** → open `crm_summary.send_daily` → **Actions → Execute**.
It arrives within a minute.

To change the time, edit **Cron Format** on that same record (e.g. `0 8 * * 1` for
Mondays at 8). **A change made there is reset to 09:00 daily by the next deploy**
(Frappe re-reads the schedule from the code on every update). For a lasting change, ask
for it in the code.

**Check it worked:** Execute, then look at the founder's phone and inbox. Desk →
**WhatsApp Message** shows the outgoing message; status turns to `sent` / `delivered` /
`read`, or `failed`.

---

## Part 8b — The "Lead / Deal" column on the Tasks page

Nothing to set up on the server: the deploy's migrate adds the field to CRM Task and
fills it in on the tasks that already exist. New tasks, ours and hand-made, get it as
they are saved. It shows the lead as "person – company" and a deal as "company – person".

1. Open `/crm/tasks`.
2. **Columns** (top right) → **Add column** → **Lead / Deal**.
3. To keep it for everyone, save the view as a public view (or set it on your public
   "My open tasks" view). Otherwise it is kept for you only.

To filter by it, use the **Filter** button and pick **Lead / Deal**. (CRM's quick
filter boxes come from its own fixed list, so it does not appear there.)

**Check it worked:** a task made for a lead shows the person and company in the new
column. Change a lead's status so a step fires, with the lead open in another tab: the
new task appears on that lead's page without a reload.

**Good to know:** the column is filled when the task is made or moved to another
lead or deal, and again whenever that lead's name or company is edited. It stays empty
when the person saving the task cannot open that lead or deal.

To hide the column from the list again, use Desk → **Customize Form** → CRM Task →
untick **In List View** on Lead / Deal. A later deploy does not turn it back on.

---

## Part 9 — Turning each part off

| To stop | Do this |
|---|---|
| One step | Delete its row in Alvoraa CRM Step Task |
| All steps for a type | Delete that type's rows |
| AI intake, email and WhatsApp together | **Server** `bench --site <site> execute alvoraa_portal.ai_leads.setup.switch_off` |
| WhatsApp intake only | Run Part 7 with an empty list: `{'forwarders': {}}` |
| One forwarder | Run Part 7 again without that number |
| The founders' summary | **Server** `bench --site <site> set-config --parse crm_founder_summary '{}'` |

---

## Part 10 — When nothing happens: where to look

| Symptom | Look here |
|---|---|
| Moved a lead, no task | The lead has a Lead Type? The step row's type and status are spelt exactly? Desk → **Error Log**, search "CRM step". |
| Step email missing | Lead has an email? Desk → **Email Queue** for the send; **Error Log** for "CRM step". |
| Forward made no lead | Desk → **WhatsApp Message**: is the message there? If not, Meta's webhook is not reaching us (Part 6.2). If it is: **Error Log** "without a valid Meta signature" means the app secret is wrong or missing. **Alvoraa AI Call Log**: a row with the outcome and a short reason. No row at all: the number is not on the list, intake is off, or the feature is not ticked. |
| Lead made but "Needs Review" | The AI was unsure, down, or the cap was reached. The call log reason says which. |
| Summary not on WhatsApp | Template APPROVED? Founder number on Meta's test list? Desk → **WhatsApp Message** status, and **WhatsApp Notification Log** for Meta's reply. The email copy should still have come. |
| Summary not by email | Desk → **Email Queue**. |
