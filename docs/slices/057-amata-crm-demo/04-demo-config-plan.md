# Slice 057 — Demo configuration plan for amata.dev.alvoraa.co

Written 2 Oct 2026. **A plan only. Nothing here has been applied anywhere.** Changing a dev
tenant's records or site config is a dev-stage action and needs Surbhi's word first. Each
step follows `02-setup-guide.md`; the part number is given.

Surbhi approved the names, steps and owners in this plan on 2 Oct 2026. Only the real
phone numbers and email addresses are still to be filled in.

Order: deploy the slice 057 code to dev → this plan, top to bottom → rehearse twice.

---

## 1. Users (guide Part 1)

| User | Name | Roles | Notes |
|---|---|---|---|
| `vinda@example.com` | Vinda | Sales User, **Sales Manager** | Owns partner onboarding; edits the step table. Sales Manager also lets her open every lead in the demo. |
| `nitin@example.com` | Nitin | Sales User | Site visits and trials |
| `sameeksha@example.com` | Sameeksha | Sales User | First call to new client leads |

For all three: **Send Welcome Email off**; Notification Settings → **Enable Email
Notifications off**; set a demo password. Check the plan's seat count.

Demo point: logging in as Sameeksha shows only her own and assigned leads and her tasks
(the CRM's own rule for Sales Users).

## 2. Fields (guide Part 2)

| Field (label) | On | Type | Options |
|---|---|---|---|
| Lead Type | CRM Lead and CRM Deal | Select | `Client Project`, `Partner Onboarding` |
| Solution Area | CRM Lead and CRM Deal | Select | the four below |

**Solution areas** (approved 2 Oct) — from Amata's
building-care line:

1. Waterproofing
2. Structural Repair and Retrofitting
3. Protective Coatings
4. Building Maintenance

Same label on lead and deal, so both carry over on conversion. Add both fields to Quick
Entry and Side Panel for Lead and Deal (CRM → Settings → Forms). Solution Area is display
only: no code reads it.

## 3. Statuses (guide Part 3)

Existing lead statuses stay (New, Contacted, Nurture, Qualified = Won, Unqualified = Lost,
Junk = Lost, Needs Review). **Add these lead statuses:**

| Lead Status | Type | Color | Position | Used by |
|---|---|---|---|---|
| Site Visit | Ongoing | orange | after Contacted | both types |
| Case Studies Sent | Ongoing | blue | after Site Visit | Partner |
| Trial | Ongoing | purple | after Case Studies Sent | Partner |
| Agreement Signed | Won | green | after Trial | Partner |

Deal statuses stay as they are: Qualification, Demo/Making, Proposal/Quotation,
Negotiation, Ready to Close, Won, Lost.

Lead source **WhatsApp** is added by the WhatsApp switch-on (section 7).

## 4. Email templates (guide Part 4)

| Template name | Subject | Body (short) |
|---|---|---|
| Amata - Thank you for meeting | `Thank you for meeting Amata, {{ first_name }}` | Thanks for the time; what Amata does; next step is a site visit. |
| Amata - Case studies | `Amata Build Care: case studies for {{ organization or first_name }}` | Three short case studies (one per solution area) and a link. |
| Amata - Partner welcome pack | `Welcome to the Amata partner network` | Agreement signed; who to call; the onboarding checklist. |
| Amata - Proposal sent | `Your proposal from Amata Build Care` | The proposal is attached separately by the salesperson; this mail says it is coming and who to call. |

## 5. Step table: Alvoraa CRM Step Task (guide Part 4)

**Partner Onboarding — Vinda's five steps, on lead statuses** (approved 2 Oct):

| # | Applies to | Status | Task title | Assign to | Due in days | Email template |
|---|---|---|---|---|---|---|
| 1 | CRM Lead | Contacted | Hold the intro meeting | vinda | 2 | Amata - Thank you for meeting |
| 2 | CRM Lead | Case Studies Sent | Follow up on the case studies | vinda | 3 | Amata - Case studies |
| 3 | CRM Lead | Site Visit | Visit a site with the partner | nitin | 5 | — |
| 4 | CRM Lead | Trial | Run the trial job and record the result | nitin | 7 | — |
| 5 | CRM Lead | Agreement Signed | Send the welcome pack and set up the partner | vinda | 1 | Amata - Partner welcome pack |

**Client Project — on lead statuses first, then deal statuses after conversion:**

| # | Applies to | Status | Task title | Assign to | Due in days | Email template |
|---|---|---|---|---|---|---|
| 6 | CRM Lead | New | Call the client within the day | sameeksha | 0 | — |
| 7 | CRM Lead | Site Visit | Schedule site visit | nitin | 2 | — |
| 8 | CRM Deal | Proposal/Quotation | Send the proposal | vinda | 2 | Amata - Proposal sent |
| 9 | CRM Deal | Negotiation | Follow up on the proposal | vinda | 3 | — |
| 10 | CRM Deal | Won | Kick-off: assign the site team | nitin | 1 | — |

Row 7 is the demo's WOW step ("he drags it to Site Visit; a task appears for Nitin, due in
two days"). Both types use Site Visit; each gets only its own task.

Note on row 6: a lead made by AI from email or WhatsApp has no Lead Type yet, so row 6
fires only when someone creates a client lead by hand, or sets the type and then moves the
lead to New again. Kept (approved 2 Oct).

### 5b. A "My open tasks" view (no code - checked in CRM 1.84)

CRM 1.84 saves list views per user or for everyone, and its filters understand `@me`
(the person looking). So one public view serves all three:

1. Log in as **vinda** (Sales Manager - only a Sales Manager or System Manager may make a
   view public). Open `/crm/tasks`.
2. Filter: **Assigned To = @me**, **Status is not Done**, **Status is not Canceled**.
   Sort by **Due Date**, oldest first.
3. Save the view as **My open tasks**, then **Make Public** (view menu).
4. Each of vinda, nitin and sameeksha opens it once and chooses **Set As Default** (and **Pin View** if they like; the
   default is per person; the CRM has no way to set it for someone else without code).

## 6. The leads mailbox and AI email intake (guide Part 5)

- Email Account: `<demo Gmail inbox>`, GMail, incoming on, not default, no
  Append To. **Surbhi types the Gmail app password.**
- CRM's own "create lead from incoming email": off.
- Server: `switch_on` with that Email Account's name, daily cap 200.
- Check first that `ai_lead_intake_api_key` is set on amata.dev and that the tenant has
  **CRM** and **AI lead intake** ticked.

## 7. WhatsApp (guide Parts 6 and 7)

- WhatsApp Account `Amata` with Meta's test-number details, a new verify token, and the
  **Meta app secret** (typed by Surbhi). Default incoming and outgoing.
- Meta webhook: `https://amata.dev.alvoraa.co/api/method/frappe_whatsapp.utils.webhook.webhook`,
  same verify token, subscribed to **messages**.
- Forwarders (server, `switch_on_whatsapp`) **[Surbhi to fill in the real numbers]**:

  ```
  {'forwarders': {'91<vinda number>': 'vinda@example.com',
                  '91<nitin number>': 'nitin@example.com',
                  '91<sameeksha number>': 'sameeksha@example.com'}}
  ```
  For a rehearsal, Surbhi's own phone can stand in as Vinda's.

## 8. Founders' summary (guide Part 8)

- Template `crm_daily_summary` (Utility, English) with the body and sample values from the
  guide, submitted **by Saturday** so Meta has time to approve it.
- Recipients (her decision, 2 Oct): all three co-founders **and Surbhi** - four numbers,
  within Meta's test-number limit of five. Add all four to Meta's recipient list.
- Site config (fill in the real numbers and addresses):
  ```
  {"whatsapp": ["91<vinda number>", "91<nitin number>", "91<sameeksha number>", "91<surbhi number>"],
   "email": ["<vinda email>", "<nitin email>", "<sameeksha email>", "<surbhi email>"],
   "template": "crm_daily_summary-en"}
  ```
  The emails here must be real inboxes, not the `@example.com` logins.
- For the demo: **Scheduled Job Type → crm_summary.send_daily → Actions → Execute**.

## 9. Sample data

Twelve leads, spread over both types and the steps. Two email addresses Surbhi controls
receive the step emails, so each template send can be shown live. I suggest Gmail "+"
addresses on the demo inbox, which all arrive in one place:
`<demo-inbox>+hotel@gmail.com` and `<demo-inbox>+partner@gmail.com`
(approved 2 Oct). Every other lead has **no email
address**, so a step email can never go to a real stranger, and never bounces off an
`example.com` address (bounces hurt the tenant's sending reputation).

Create the leads **before** filling the step table (section 5), so loading them does not
make a pile of tasks and emails. Then make the few tasks the demo needs by moving those
leads one step after the table is filled.

| # | Lead (person, company) | Lead Type | Solution Area | Status | Owner | Email |
|---|---|---|---|---|---|---|
| 1 | Prakash Shetty, Hotel Sea Breeze, Kankanady | Client Project | Waterproofing | New | sameeksha | `<demo-inbox>+hotel@gmail.com` |
| 2 | Anita Rao, Sapthagiri Apartments Association | Client Project | Waterproofing | Contacted | sameeksha | — |
| 3 | Ramesh Kamath, Kamath Textiles warehouse | Client Project | Protective Coatings | Site Visit | nitin | — |
| 4 | Dr. Meera Pai, Pai Nursing Home | Client Project | Structural Repair and Retrofitting | Site Visit | nitin | — |
| 5 | Joseph D'Souza, St. Aloysius parish hall | Client Project | Building Maintenance | Nurture | sameeksha | — |
| 6 | Harish Bhat, Bhat Builders | Client Project | Structural Repair and Retrofitting | Qualified → converted to deal at **Proposal/Quotation** | vinda | — |
| 7 | Suma Hegde, Coastal Malls | Client Project | Protective Coatings | Qualified → converted to deal, **Won**, value 4,50,000 | vinda | — |
| 8 | Kiran Naik, Naik Waterproofing Contractors | Partner Onboarding | Waterproofing | Contacted | vinda | `<demo-inbox>+partner@gmail.com` |
| 9 | Rohit Shenoy, Shenoy Paints and Coatings | Partner Onboarding | Protective Coatings | Case Studies Sent | vinda | — |
| 10 | Fatima Sheikh, Udupi Repairs Collective | Partner Onboarding | Structural Repair and Retrofitting | Site Visit | nitin | — |
| 11 | Vivek Alva, Alva Facility Services | Partner Onboarding | Building Maintenance | Trial | nitin | — |
| 12 | Lakshmi Prabhu, Prabhu Engineers | Partner Onboarding | Waterproofing | Agreement Signed | vinda | — |

Then, after section 5 is in place:

- Move lead 2 to **Site Visit** → Nitin gets "Schedule site visit" (a real task for the list).
- Move lead 9 back to Contacted and forward to Case Studies Sent → a task for Vinda.
- Set the due date of two open tasks to yesterday (in the task) so the summary shows
  **Overdue tasks: 2**.
- Lead 7's deal is Won today, so the summary shows one deal won.

Keep **lead 1** at New and **lead 8** at Contacted for the live demo: moving lead 8 to
Case Studies Sent sends the case-studies email to Surbhi's inbox on screen; moving
lead 1 to Site Visit gives Nitin his task.

## 10. Rehearsal checklist

1. Email to `<demo Gmail inbox>` from a personal address → lead within two
   minutes, AI note present.
2. Forward the hotel message from the listed phone → lead within a minute, owner Vinda.
   Same from an unlisted phone → nothing.
3. Set the forwarded lead's type to Client Project, move it to Site Visit → Nitin's task.
4. Move lead 8 to Case Studies Sent → task for Vinda + email in Surbhi's inbox.
5. Log in as Sameeksha → only her leads and tasks.
6. Execute the summary → WhatsApp on all four phones and the email copy.
7. Afterwards: set test leads to Junk, or delete them, so the summary stays believable.
