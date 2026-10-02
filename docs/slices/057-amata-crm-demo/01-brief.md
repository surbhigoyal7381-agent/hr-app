# Slice 057 - Amata CRM demo (Mon 5 / Tue 6 Oct 2026)

Status: draft for Surbhi to approve. I recommend; she decides.

## 1. Outcome and persona
Vinda, Nitin and Sameeksha (Amata) see that one lead, from any channel, becomes a CRM record whose next step is already a task with a named owner and a due date. And founders get a pipeline summary on WhatsApp without opening an app.

Job: "When a lead reaches me by email, WhatsApp or a meeting note, I want it in one place with the next step already assigned, so nothing waits on me remembering."
Persona: CXO/founder (summary), HR-Manager-equivalent = sales lead (stage moves), Employee = site staff (own tasks only).

## 2. What already exists (checked quickly)
- Confirmed: no WhatsApp or stage-task code in our repo. The CRM app source is not in the repo; I could not read it.
- [recall - verify] Frappe CRM ships a WhatsApp tab only through the separate Frappe WhatsApp app. It does not turn an incoming message into a lead by AI, and has no allow-list.
- [recall - verify] Frappe CRM has Tasks and standard Assignment Rules, but no "status X creates task Y for person Z" table.
- Confirmed: email AI intake exists (`alvoraa_portal/ai_leads/intake.py`, slice 043). We reuse its guards, cost cap and lead-making.
- Action before build: 15 minutes on the dev bench to confirm the three recalls above. If CRM or Frappe WhatsApp does it, we configure instead.

## 3. The WOW (inside the demo)
Vinda forwards a real-looking WhatsApp message from his phone ("Hotel in Kankanady, bathroom leaks, wants quote") to the Amata number. Within a minute, on the big screen: a new lead appears, tagged "Client project". He drags it to "Site visit". A task appears: "Schedule site visit - Nitin - due Thursday", with the email template ready. Then his phone buzzes: "Pipeline today: 6 open leads, 2 due this week. Open: <link>".

## 4. Demo script (10 min)
1. 0:00 Lead list and card. Two lead types, each with its own steps (1 min).
2. 1:00 Email lead: send a mail to `<demo Gmail inbox>`; show it arrive as a lead with the AI note (2 min).
3. 3:00 WhatsApp forward from an allow-listed number: lead created (2 min). Show a non-listed number is ignored.
4. 5:00 Move a client lead one stage; task appears for Nitin with due date (2 min).
5. 7:00 Partner lead: meet -> case studies email (template fires) -> site visit -> trial -> agreement (1 min).
6. 8:00 Log in as Sameeksha: sees only her tasks and leads. Then the WhatsApp summary arrives (2 min).
Hindi: the labels are English; AI reads Hindi messages. Say this honestly. Do not promise a Hindi screen.

## 5. Smallest build (rung: 3 customisation + 4 small new code; no new app)
**1. Stage to task.** One child table on the existing CRM Lead type setting ("Lead type", "Stage", "Task title", "Assign to (user)", "Due in days", optional "Email template"). One server hook on CRM Lead status change reads the table and inserts a standard CRM Task. Lead type is one Custom Field on CRM Lead. No new DocType unless CRM has no settings record to hang the table on. Rejected: a rules engine, a workflow per type, Assignment Rules (they assign leads, not create step tasks). Doc: one page, `docs/slices/057-amata-crm-demo/02-stage-task-setup.md`, with screenshots, so Surbhi can set up other tenants.
**2. WhatsApp AI intake.** One whitelisted webhook for Meta's test number. Check the sender against a short allow-list (Custom Field/table in AI settings). Not on the list: drop it, store nothing. On the list: reuse the email path's cost cap, text cleaning, model call and `make_lead`. Text only. Deterministic: allow-list, cap, duplicate-sender check. AI: "is this a lead?" and field extraction. If AI is down: create a bare lead with the raw text in a note (as email does). Surbhi sets up the Meta test number from a short guide I will not write until she asks.
**3. Founders' summary.** One scheduled function: counts of open leads by type and stage, tasks due this week, overdue tasks, plus a link to the CRM list. Sent as plain text to the founders' numbers. No dashboard. Aggregate counts only, no per-person ranking.
Also: sample data script (Vinda, Nitin, Sameeksha, example.com logins; `<demo Gmail inbox>` mailbox). Demo folder only.

## 6. Kano (proxy)
Stage to task: Performance (buyers compare CRMs on follow-up discipline). WhatsApp lead intake: Attractive (few competitors do AI intake from forwards). Founder summary on WhatsApp: Attractive. Easy CRM and role views: Must-be. Evidence that would change this: Amata's reaction in the demo.

## 7. Success criteria
- Demo runs end to end with zero manual database edits; rehearsed twice by Sun 4 Oct. Instrument: rehearsal checklist.
- Each lead moves one stage and the task shows within 5 seconds. Check on the day.
- Amata says "yes, proceed" or names the missing piece. Lagging; Surbhi records it. Baseline: none.
- AI cost per demo day under Rs 50. Read from the existing AI log. [ASSUMPTION: the log holds cost]

## 8. NOT in the demo (Sprint 1+)
Mobile app (their phase 3). Hindi screens. PLAUD device (it emails summaries, so it rides on the email intake; we say so, we do not build for it). Business-initiated WhatsApp and Meta-approved templates. WhatsApp attachments, voice notes, replies from CRM. Project-health reports beyond lead counts. Own Meta business number. Recurring tasks, escalation, SLA timers. Per-user dashboards.

## 9. Risks
- **Deadline: Monday.** Three builds in about 2 working days. If one slips, cut order: summary link, then the summary, then email template on tasks. Never cut the stage-to-task or the WhatsApp intake.
- **Meta rules.** A business can message freely only within 24 hours of the user's last message. The founder summary is business-initiated, so on production it needs an approved template. For the demo, founders message the test number first, which opens the window. The test number also only messages numbers added in Meta's console. Do this setup by Sat.
- **Meta test number is not production.** Real use needs Amata's own number and verification. Say so in the demo.
- **AI cost.** Reuse the 200/day cap from slice 043. Allow-list keeps spam out.
- **Privacy.** Forwarded messages contain third parties' names and numbers. Compliance: ⚠ COMPLIANCE - Surbhi confirms who tells the forwarder that forwarded text goes to an AI model; the DPDP duty sits with Amata. Mitigations: allow-list, keep only the lead text, drop unlisted senders unstored, no group chats.
- **Wrong hook.** A hook on CRM Lead touches every lead. Test with a lead type that has no rows: it must do nothing.

## Subtract pass
Removed: a WhatsApp reply bot, a Hindi translation step, a summary dashboard, and a task-template DocType. Kept nothing extra.

## Open questions
- Surbhi (blocks build): do the 3 recalls in section 2 hold? I will check on the bench first.
- Surbhi (blocks summary): which founder numbers receive it, and is a plain link to the CRM list enough?
- Surbhi (blocks go): confirm the privacy line on forwarded messages.
## Assumptions
- [ASSUMPTION] Meta test number can receive webhooks on dev with a public URL.
- [ASSUMPTION] Demo runs on a dev tenant, not production.
## Kill criteria
Stop and demo email-only if the Meta webhook is not receiving by Sun 4 Oct noon.
