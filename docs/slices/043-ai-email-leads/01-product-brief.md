---
slice: 043-ai-email-leads
artifact: 01-product-brief
author: hrms-product-manager
date: 2026-09-24
status: draft — recommendation; Surbhi decides
inputs: [the user's request (verbatim in 02 §0), 02-functional-spec.md, 01c-security-privacy-requirements.md, docs/sargam_metals/02-ceo-demo-storyline.md, .claude/context/product-context.md, .claude/context/handoff-contract.md, CLAUDE.md, vendor pages read 24 Sep 2026 (listed in §3)]
---

# 043 — Leads from email into Frappe CRM, with AI filling the columns

**The outcome in one sentence:** a real enquiry that lands in Sargam's sales mailbox
becomes a CRM lead by itself — person, company, phone, industry, territory and a
one-paragraph "what they want" already filled — and the doubtful ones wait in a
"Needs review" list for a named person, so a salesperson calls instead of types.

**Bad news first.**

1. **This brief is written after the spec and the security requirements, not before.**
   There is no `01a` (UX scan) and no `07 §1` (DevOps first look). The user chose this
   order and took the decisions (spec, "Decisions taken by the user, 24 Sep 2026"). So
   this brief fits the spec; it does not redirect it. Where the brief has no design or
   run-side evidence, it says so.
2. **The spec (`02`) and the security requirements (`01c`) disagree in nine places**
   because they were written in parallel. None is fatal. All must be reconciled by the
   analyst before the engineer's `00`. The list is in §10.
3. **Frappe CRM already turns every unknown sender into a lead** (spec G-2, G-3). So
   the honest job is not "create leads from email". It is "stop creating a lead for every
   newsletter, and fill the columns a person would otherwise type". If the demo audience
   expects the first, they already have it for free.

I am not a lawyer. Legal points below are questions for counsel, not rulings.

---

## 1 · Job to be done

> "As Sargam's sales head, when an RFQ for anodes lands in `sales@` on a Monday, I want
> it to be in the CRM with the company, the contact and what they want already filled,
> so my team calls the shipyard back today instead of finding the email on Thursday."

**Persona:** the **Sales Manager** and **Sales User** of a tenant that has bought the
CRM. **This slice has no HR persona.** CXO, HR Manager and Employee see nothing, and
the spec's permission matrix says so as must-not rows (spec §7, US-11).

**Current pain — a story, not a number.** The Sargam storyline (§6, lead 6) has an
enquiry from a pipeline company that arrived by email and sits at "needs technical
reply". That is the shape of the problem: the enquiry exists in someone's inbox, the CRM
does not know about it, and nobody can see it is waiting. **Evidence required:** there is
no baseline for "enquiries per week" or "hours from email to CRM" at Sargam or anyone
else. Measure it in the first two weeks on a real mailbox (§7).

---

## 2 · Kano class and demand

**Class: Performance (proxy).** Reasoning:

- The **floor is Must-be**: every CRM in the comparison creates a record from an inbound
  email, and Frappe CRM already does it (badly — no filter, no columns). Its absence would
  cost deals; its presence earns nothing.
- The **AI extraction into columns** is where buyers compare vendors: how many fields, how
  accurate, does it filter the noise. "More is better, less is worse" — that is
  Performance.
- It is **not Attractive**: Zoho, HubSpot, Freshsales and Salesforce all ship a version
  (§3). Nobody lights up at "it reads the email"; they light up at "it was right".

**Demand evidence, labelled:**

| Evidence | Label |
|---|---|
| The user's own request, verbatim in the spec | seen — 24 Sep 2026 |
| Sargam storyline: one of eight demo leads arrives by email; the proposal to Sargam mentioned "AI agent email features" | seen — 23 Sep 2026 |
| No customer, demo prospect or support ticket has asked for it yet | honest gap — Sargam is the first buyer we would show it to |

**What would change the class:** if three demo prospects ask for it unprompted, it drifts
toward Must-be for the CRM add-on. If the 200-email test shows precision under 80 %, it
is a liability, not a Performance feature, and should not be sold (§11 kill criteria).

---

## 3 · Competitive analysis — whole products

| Capability | Zoho CRM | HubSpot | Freshsales | Salesforce | LeadSquared (Indian SME) | Frappe CRM today | **Us after this slice** |
|---|---|---|---|---|---|---|---|
| Lead created from an inbound email | Yes, via **Email Parser** — rule and template mapping, no AI; **Enterprise edition and above** (read 24 Sep 2026, help.zoho.com) | **No** — AI fills properties on *existing* contacts only; "will not create new contacts" (read 24 Sep 2026, knowledge.hubspot.com) | Not as a native email-to-lead; leads come from forms, chat, and are then enriched `[verify]` | Einstein Activity Capture links mail to *existing* leads and contacts; Agentforce nurtures leads once they exist `[verify create-from-email]` | Yes — an inbound mail from an unknown address creates a lead (Service CRM, Gmail/Outlook) (read 24 Sep 2026, help.leadsquared.com) | Yes — every unknown sender, no filter (confirmed in source, spec G-3) | Yes, **only when the model says it is an enquiry** |
| Filters newsletters, auto-replies, suppliers | By sender/subject rules the admin writes | n/a | n/a | Flow rules to exclude auto-replies (read 24 Sep 2026) | Not found `[verify]` | None | Header rules in code, then the model's yes/no |
| Fields filled from the email body | Only fields the admin mapped from a template; **Zia** enriches from signatures (read 24 Sep 2026) | 11 properties from signature and body, first email only | Enrichment from public databases, not from the email text | From addresses; body not extracted `[verify]` | Sender details only `[verify]` | First name, last name, email | Name, organisation, phone, job title, industry, territory, employee band, plus a summary note |
| Uncertain cases go to a person | "Parse failed" report and "Parse Again" | n/a | n/a | n/a | n/a | n/a | **"Needs review" queue, named reviewer, one-click accept/reject** |
| Audit of what the AI saw and said | Not found | Not found | Not found | Einstein Trust Layer audit `[verify scope]` | Not found | n/a | Per-call log: model, prompt version, cost, output, human decision |
| Where it sits in pricing | Enterprise+ | All plans, incl. free | Growth+ `[verify]` | Sales Cloud + Einstein/Agentforce add-on `[verify]` | Bundled `[verify]` | Free, in the app | Opt-in add-on requiring the `crm` feature; price open (OQ-9) |

**What we will deliberately NOT do that they do, and why it is better for our user:**

- **No template-based parser (Zoho).** A metals exporter gets RFQs in fifty formats.
  Nobody at Sargam will maintain templates. The model reads intent; the admin maintains
  nothing but an ignore list.
- **No enrichment from third-party databases (Freshsales, HubSpot Breeze).** Only what
  the sender wrote leaves the tenant. Nothing is bought about the prospect. This is the
  version that passes a DPDP review.
- **No AI reply, no nurture agent (Salesforce Agentforce).** Extraction only. A message
  to a prospect is written by a person. A separate brief if ever wanted (spec G-13).
- **No attachment reading.** Filenames only (spec G-14). A tender PDF is the next slice
  and changes cost and privacy surface by an order of magnitude.

## 3a · Three ways to solve it, and could we not build it

| Way | What it is | Verdict |
|---|---|---|
| **Not build** | Turn on Frappe CRM's own "Create Lead from Incoming Emails" and its sender/subject filters | **Rejected** — it has no filter at all; Sargam would get one empty lead per newsletter, then stop trusting the list |
| **Conventional** | A Zoho-style parser: admin writes regex/templates per mailbox | **Rejected** — maintenance falls on the tenant; wrong for messy Indian B2B mail |
| **Better** *(chosen)* | Header rules first (no cost), one extraction-only model call, a review queue for doubt, fallback to a bare lead when the AI is down | **Chosen** — the spec's design |
| **Reimagined** | Model also drafts the reply, reads the PDF, scores the lead | **Deferred** — each is its own risk class and its own brief |

**Which of the four cost levels:** *new code, small* — custom fields on existing
doctypes, one new log DocType, one background job. Not a new app, not a new module.
Configuration alone was rejected because Frappe CRM has no hook between "email arrived"
and "lead created" that could ask a question first (spec G-4).

---

## 4 · Persona by persona — what changes, and in which slice

| Persona | What this gives them | Job it serves | Slice 1? | Why |
|---|---|---|---|---|
| **Sales User** | Opens the CRM and the RFQ is already a lead with phone, company and a summary; the email is on its timeline | Call today, not Thursday | Yes | The core loop |
| **Sales Manager / named reviewer** | A "Needs review" list; accept or reject in one click; the AI log behind any lead | Nothing dropped, nothing wrong reaches the team | Yes | Without an owner, the queue is where mail goes to rot (spec §2) |
| **Tenant admin** (System Manager) | Ticks one mailbox, names the reviewer, reads a plain notice that email text goes to a model provider | Turn it on safely | Yes (one mailbox) | Several mailboxes, cap and kill switch are slice 2 (D-7) |
| **CXO** | Nothing on screen. Indirectly: the CRM list the demo shows "looks like a real week" | Trust the pipeline | No new screen | A CXO without a Sales role sees no lead (spec §7) |
| **Employee / HR Manager** | **Nothing — by design.** A prospect's phone number stays with sales | — | Must-not, tested (US-11) | New category of personal data on the tenant |
| **The prospect** | Gets called back sooner. Their text is read by a model at a US provider for up to 30 days | — | — | The honest downside; §8 |

There is no employee-portal enhancement in this slice. The `01a` scan that would list
them was not produced; none is needed for a sales-only slice.

---

## 5 · The WOW moment — for the Sargam CEO demo

**Screen:** CRM → Leads, the list the CEO saw ten minutes earlier with eight seeded
leads. **Moment:** the presenter sends a short RFQ from a phone to the demo mailbox
("We need 60 hull anodes for two tugs at Mazagon, can you quote by Friday? — Ravi
Kulkarni, Konkan Shipbuilders, +91 98xxx") and keeps talking. Within the 10-minute pull
window a ninth row appears: **Konkan Shipbuilders · Ravi Kulkarni · +91 98xxx ·
Shipbuilding · India · New · "AI-created, 91 %"**. The presenter opens it. The note reads:
*"AI-generated summary — check against the email below. 60 hull anodes for two tugs at
Mazagon, quote wanted by Friday."* The email is on the timeline underneath.

**Micro-copy the CEO hears:** "Nobody typed that. Your salesperson's job is now the
phone call, not the data entry. And if the model is not sure, it asks a person — it
never guesses on your behalf."

**Demo trap:** the 10-minute pull is Frappe's cron. Send the email *before* Block 6 so
it appears during the CRM block. Rehearse with the exact fixture. If it does not appear,
say "it runs every ten minutes" and move on — never refresh in front of the CEO.

---

## 6 · The thin slice — D-7, as the user chose

**Slice one — the core loop on one mailbox.** Opt-in feature `crm_ai_intake` (requires
`crm`, in no bundle) · the rule screen (custom fields on FCRM Settings and one tick on
Email Account; refuses the CRM's own two email-to-lead mechanisms) · header filters ·
one extraction-only model call · lead creation with columns filled and the email
attached · the "Needs review" status and accept/reject · the AI log and the read-only
provenance fields on the lead · fallback to a bare "Needs review" lead when the AI is
down · the turn-on notice.

**Slice two — explicitly not in slice one:** several mailboxes and the "which mailbox"
column (US-16) · cross-sender dedupe by company domain (US-5, D-4) · backfill of past
mail (US-9) · the daily cost cap (US-8) · the tenant kill switch with reason (US-14).

**Not doing at all (spec §14):** AI replies · attachment contents · product-table
matching · lead scoring · classic ERPNext Lead · WhatsApp or web-form intake ·
tenant-supplied keys · multi-company scoping of leads.

**One thing I recommend adding back to slice one — the user's decision stands if not:**
the **site-config ceiling** from SEC-19 (a hard number only Alvoraa can change, default
500 a day). It is a few lines. Without it, slice one must never be pointed at a real
mailbox — a spam flood would run the bill with no stop. For the demo mailbox, which
receives only what the team sends (PRIV-12), it does not matter.

---

## 7 · Success criteria

| Measure | Baseline | Target | How it is measured |
|---|---|---|---|
| **Precision on auto-accepted leads** — of leads the model accepted alone, share a person agrees are real enquiries | unknown — measure first | ≥ 90 % on the 200-email test set (D-2) | 200 labelled real emails, replayed through the pipeline; log rows vs labels |
| **Recall** — of real enquiries in the set, share that became a lead (auto or via review) | unknown | ≥ 95 %; **no real enquiry silently dropped** | Same test; "Not a lead" rows checked against labels |
| **Review-queue share** — share of qualifying emails that need a human | unknown | ≤ 25 % after the first month | Log `outcome` counts per week |
| **Time from email arrival to lead visible** (p95) | unknown; today "until someone reads the inbox" | ≤ 15 minutes | Communication `creation` vs lead `creation` |
| **Cost per lead created** | none | ≤ ₹1 on the cheapest model class `[verify prices]` | Log `cost_inr` summed / leads created |
| **Correction rate** — AI leads edited by a person within 7 days | unknown | trend down per prompt version | CRM `Version` rows on AI-created leads |

Because this slice includes AI: acceptance rate (auto-accepted share), override rate
(edited or rejected), and escalation rate (queue share) are all in the table above.
Logins and page views are not measures.

---

## 8 · Run-side reality, thriving-workplace lens, regulatory read

**Run-side (no `07 §1` exists; from the spec):** no new app; one job on the `default`
queue; one new DocType; outbound HTTPS to one provider; ~₹0.25 per email on the cheapest
Claude class `[verify]`, so ~₹50 a day at the 200-email cap. Nothing here changes the
slice's size. **Recommend** DevOps writes `07 §1–3` before the engineer's `00`.

| Lens | One line |
|---|---|
| Engagement | The salesperson gets momentum — a call to make, not a form to fill. |
| Collaboration | The enquiry is visible to the whole sales team the moment it arrives, not when one inbox owner forwards it. |
| Inclusiveness | Hindi, Tamil or Arabic enquiries are read and summarised in English; the original stays. No employee is excluded because none is in scope. |
| Transparency | Every AI-created lead says so, with its confidence and its log. The prospect is not told — that is the tenant's notice duty (Q-1). |

**Regulatory read (four lines):**

1. **Regime:** DPDP (prospect's personal data sent to a US sub-processor); CERT-In if a
   key or a mis-ticked mailbox leaks; EU AI Act minimal-risk on the security engineer's
   reading; no employment law.
2. **Whose duty:** the **tenant's** — it is the Data Fiduciary for its prospects. We are
   its processor. The feature that wins the security review is the one that helps the
   tenant discharge that duty: the recorded turn-on acceptance (PRIV-1), the log, the
   erase-by-address tool (PRIV-7).
3. **Newly possible:** prospect text leaves the tenant automatically, to a model, with
   no human looking first; free text from strangers becomes structured CRM columns.
4. **Front page test:** "Indian exporter's AI sends customer emails to a US company"
   — defensible only if the tenant accepted it knowingly, the provider does not train on
   it, and 30-day retention is stated truthfully. All three are in `01c`.

⚠ COMPLIANCE — counsel's Q-1 (lawful basis) and Q-2 (transfer) block a **paying**
tenant, not the demo. Owner: Surbhi with counsel.

---

## 9 · Risks — red-teamed

| Risk | What breaks | Cheapest way to find out |
|---|---|---|
| The model is wrong with high confidence (hallucinated phone) | Salesperson calls a wrong number; trust in the list drops | The span check (spec AC-9) plus the 200-email test **before** the demo |
| 10× the mail (a spam flood) in slice one | No cap: every email costs; AI-down fallback makes every spam a "Needs review" lead | The site-config ceiling (§6) or keep slice one on the demo mailbox only |
| Admin ticks the HR mailbox | Payslip queries go to a US provider | SEC-8's refusal in `validate` — **missing from the spec**, §10 |
| Reviewer leaves; nobody owns the queue | Enquiries rot in "Needs review" | Reviewer is mandatory when enabled (AC-1); add "reviewer's user disabled" to the checks in slice two |
| Provider changes model IDs or prices | Cost line wrong; call fails | IDs and prices are `[verify]` throughout; engineer confirms on day one |
| Frappe's `Communication` list leaks intake mail to an Employee | A prospect's message readable by staff — the highest-severity defect here | **Pre-code blocker (a)** below |

**The two pre-code blockers, already named in the spec:**
(a) prove on the local bench that an Employee cannot list a sales mailbox's
`Communication` rows through `/api/resource` (OQ-8); if they can, fix it in the CRM
feature first. (b) counsel's note and the DPA Annex 3 row for the hosted model. Both
block a paying tenant, not the demo.

---

## 10 · Where the spec and `01c` disagree — the analyst reconciles before `00`

| # | Spec (`02`) | Security (`01c`) | My recommendation |
|---|---|---|---|
| 1 | Log `Alvoraa AI Action Log` stores `model_output` JSON (which holds extracted name and phone) and an `error` text | Log `Alvoraa AI Call Log` holds **no content** — no names, values or reasons (SEC-17) | `01c` wins on content: reasons and output go on the lead/queue row, not the log. Keep one DocType |
| 2 | Log kept 18 months | 12 months (PRIV-6) | Counsel decides (Q-5); build the number as a setting |
| 3 | Auto-accept ≥ 80 %, not-a-lead ≥ 85 % | Auto-create default 0.85, floor 0.7 (SEC-3) | Take `01c`'s default and floor; measure on the 200 emails |
| 4 | Mailbox tick refuses only the CRM's own two mechanisms | Also refuses `default_incoming`, `hr@`/`payroll@`-style names, HR-role users (SEC-8) | **Add SEC-8 to the spec** — it is the single biggest blast radius |
| 5 | Full sender address sent to the model | Local part masked to first character (SEC-10) | `01c` wins; the code matches on the full address |
| 6 | Model called with tool use, `tool_choice` forced | No tools; structured output via `output_config.format` json_schema (SEC-1, verified) | `01c` wins — it was verified against the docs on 24 Sep |
| 7 | One-line notice on the switch | Recorded acceptance: user, time, text version, re-asked on change (PRIV-1) | `01c` wins; same shape as slice 013's notices |
| 8 | Lead `owner` = Administrator | A dedicated no-login system user `ai-leads@<site>` (SEC-16) | `01c` wins — "who made this" must be honest |
| 9 | Custom-field prefixes `alvoraa_ai_intake_` / `alvoraa_intake_state` | `alvoraa_ai_` | Either; pick one and use it everywhere |

Also for the analyst: SEC-19 ceiling, SEC-20 breaker and SEC-21 platform switch land in
slice two under D-7, except the ceiling if the user takes §6's recommendation.

---

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | Does the site-config ceiling (SEC-19) come into slice one? My recommendation: yes | Surbhi | Whether slice one may touch a real mailbox |
| 2 | Price of the add-on (OQ-9) — the "what does it cost" line in the Sargam demo | Surbhi | The console entry; the demo answer |
| 3 | Counsel's Q-1 / Q-2 and the retention numbers (Q-5) | Counsel, Surbhi | A paying tenant; §10 rows 2 |
| 4 | Who writes `07 §1–3` and whether a `01b` design check is wanted for the settings block and accept/reject buttons | Surbhi | The engineer's `00`; the Ready check |
| 5 | Are the 200 test emails available — real, from Sargam or another mailbox, with consent to use them for testing? | Surbhi | Every success measure in §7 |

## Assumptions

- `[ASSUMPTION]` Sargam will let a demo mailbox be used, receiving only team-written
  emails (D-6, PRIV-12).
- `[ASSUMPTION]` The CRM's Vue lead page shows the custom fields without a CRM code
  change (spec §15 `[verify]`).
- `[ASSUMPTION]` Sargam-scale volume: tens of enquiries a week, under 300 emails a day.
- `[ASSUMPTION]` Model IDs, prices and API parameters are as `01c` verified on 24 Sep
  2026; the spec's from-memory values are superseded by them.
- `[ASSUMPTION]` Competitor claims marked `[verify]` were not confirmed on vendor pages
  today; the ones dated "read 24 Sep 2026" were.

## Kill criteria

Stop and do not sell it if: precision on auto-accepted leads is under 80 % on the
200-email test after one prompt revision; or blocker (a) shows an Employee can read
intake mail and the fix is not in the CRM feature; or counsel says the tenant has no
lawful basis to send prospect email to a hosted model. Stop the **demo** segment if the
fixture email has not appeared as a lead in three rehearsals in a row.

## Handoff note

To the analyst: reconcile the nine rows in §10 in `02`, adding SEC-8 in full — do not
soften it to a warning. Mark which stories are slice one and slice two per D-7 and §6.
To the engineer, after that: `01c`'s call pattern (no tools, structured output) is the
verified one; the spec's tool-use text is from memory. To DevOps: `07 §1–3` are missing
and the Ready check fails without them. I agree with the spec's reframing (filter and
fill, not "create leads") and with every user decision D-1 to D-7; my one push-back is
the ceiling in slice one (§6).
