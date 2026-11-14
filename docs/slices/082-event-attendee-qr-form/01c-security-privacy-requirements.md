---
slice: 082-event-attendee-qr-form
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-13
status: draft
inputs: [01-product-brief.md, 01b-ux-design.md (incl. §13), prototype-v2.html, 07-devops-inputs.md §1-§2 (OPS-1..OPS-17), security-compliance-baseline.md, compliance-feature-map.md, data-doors.md, no-over-engineering.md]
youtrack: ALV-339
---

# 082 · Event attendee QR form · Security and privacy requirements

I recommend. Surbhi decides. I am not a lawyer; every ⚠ COMPLIANCE item needs counsel.

## 0. The answer first

**Bad news first.**

1. **The guest save is a hole in the wall, and it cannot be closed later without breaking
   printed QR codes.** Anyone on the internet can write a CRM Lead into the tenant. Only the
   field allow-list, the limit and the "say nothing back" rule stand between the internet and
   the lead list. SEC-1 to SEC-5 are those rules.
2. **Deleting a CRM Lead does not erase the person.** Frappe keeps a full copy of every deleted
   record in *Deleted Document*, and old values stay in *Version* rows (Inference: standard
   Frappe delete behaviour; not re-read in this run). A "delete after 6 months" that leaves
   those copies is not erasure. PRIV-5.
3. **The staff-name leak (G2) is a site-wide switch any Sales Manager can flip with one
   click**, and it outlives the form. Banning Link fields on our page does not stop it,
   because CRM's own `/crm-form/` page still exists. SEC-6 closes it in the permission layer.
4. **I could not check three things** (see §9): the CRM source (Docker was not running, so I
   rely on the UX and DevOps reads of CRM v1.84.0); any real tenant's roles (no named CRM
   tenant yet, brief MK1); and the request guard `data-doors.md` names — no
   `request_guard.py` exists in `alvoraa_portal/alvoraa_portal/` (Verified: `find`, 13 Nov).

**Counts:** 10 SEC, 6 PRIV. **Rung:** customisation plus one small guest endpoint and one
small page (rung 3-4), as already agreed (D6). No new DocType, app, job, queue or service.

## 1. Threat model in four lines

| Question | Answer for this slice |
|---|---|
| **Who wants it, cheapest way?** | (a) A **competitor or scraper** wants the attendee list: cheapest is a read-back door (an echo, a lead ID, a link search, an existing Guest permission row). (b) A **spammer or prankster** with a photo of the poster: cheapest is scripting the save call. (c) A **tenant staff login** (Employee-only or Sales User) reading every attendee through `/api/resource/CRM Lead`. (d) A **departing Sales Manager** exporting the list — allowed by design (C2); only detectable, not preventable. |
| **Blast radius of one mistake** | **One tenant's whole lead list** if a guest read door opens (every lead, not only event leads). **Up to 500 staff names** of one tenant through G2. Cross-tenant: low — each tenant is its own site and database, and the site is picked by Host header (Fact per OPS-7 / DevOps §1). |
| **What becomes possible that was not** | Unauthenticated **writes** of personal data from the public into the CRM; collection from people who are **not employees and have no login**, so no in-product rights path exists for them; organiser-defined questions that may collect anything. |
| **How would we find out** | Today, only "a customer tells us". Spam shows as a lead-count jump per event in the saved view (SEC-5). A Guest permission row is refused at save (SEC-6), and counted before release. There is no log of list reads (data-doors), so a read leak would be invisible — which is why the read doors must be shut, not watched. |

## 2. Data inventory

All on **CRM Lead** (D7-A). Class: `internal` / `sensitive` per compliance-feature-map A1
(A1 is not built; these classes are written here so the BA can carry them).

| Field | Class | Purpose | Retention | Who may see |
|---|---|---|---|---|
| Name, mobile, email | sensitive (contact) | Follow up this event | 6 months after event, unless "news" ticked `[ASSUMPTION — counsel Q4]` | Sales Manager; Sales User only if assigned |
| Event form (stamp) | internal | Which event | With the lead | Same |
| Event rating, Event comment | internal (free text may hold anything) | Judge the event, call unhappy people | With the lead | Same. Speakers: none (C4 narrow) |
| Consent: this event | internal | Lawful basis record | With the lead, then erased with it | Same |
| Consent: news | internal | Marketing permission | Until withdrawn, then erase or revert to 6-month rule `[ASSUMPTION]` | Same |
| Extra question answers (custom fields) | set by the System Manager at field creation; **never** statutory-ID, health, religion, caste, bank (PRIV-2) | Per question, stated in the notice | With the lead | Same |
| Caller IP | internal | Rate limit only | Hashed key in Redis, 1 h; nginx access log per existing policy | Ops only |
| Notice text shown | internal | Prove what the person agreed to | As long as any lead from that form exists | Sales Manager, System Manager |

## 3. Access intent — and who must NOT see what

Narrower option on every brief conflict (C1-C5), as agreed 13 Nov 2026.

| Persona | May | Must NOT |
|---|---|---|
| **Guest (attendee, anyone with the link)** | Load a published form; send one entry; see "Thank you" | Read any lead, count, lead ID, own answers after send, staff name, any record through link search; see the organiser box; tell a closed form from one that never existed |
| **Employee-only login** (tenant HR portal staff) | Nothing on CRM Lead | Any CRM Lead row or field through any data-doors door |
| **Sales User** (door staff, if they have a login) | Leads assigned to them | The event list as a whole (C1); export (C2); speakers' view |
| **Sales Manager** | All leads; correct, assign, delete; export inside the tenant | Create Custom Fields (D8-A); grant Guest access to any doctype (SEC-6); email people without "news" ticked (C3 — a rule in the setup guide and the saved view, see worries) |
| **System Manager** | Create the question fields | — |
| **CXO without Sales Manager** | Counts per event (C5) | Individual rows |
| **Alvora staff** | Only on the organiser's request, for a fault | Routine browsing (existing support practice; not changed here) |

## 4. Obligations engaged

| Obligation | Source | Last checked | What it needs here |
|---|---|---|---|
| Notice before collection, itemised, English or Eighth-Schedule language | DPDP Act s.5; baseline §2 | 24 Aug 2026 (81 days, not stale) | Notice under the consent tick, EN + HI (PRIV-3) |
| Consent: free, specific, unticked, withdrawable as easily as given | DPDP Act s.6; baseline §2 | 24 Aug 2026 | Two separate ticks, both unticked; withdrawal path (PRIV-3, PRIV-4) |
| Erasure when the purpose is served | DPDP Act s.8(7); counsel's "no soft-delete for ever" (memory, 18 Sep 2026) | 24 Aug 2026 | PRIV-5 |
| Children: verifiable parental consent | DPDP Act s.9; **DPDP Rules 2025 Rule 10, in force 13 May 2027** per secondary sources | **13 Nov 2026** (SCC Online, Legal500; gazette not read) | ⚠ C-1 |
| Processor acts only under a valid contract with the fiduciary | DPDP Act s.8(2) `[recall — not re-verified today]` | Not verified this run | ⚠ C-2 |
| Aadhaar numbers not collected without a legal basis | Aadhaar Act s.29 and Aadhaar regulations `[recall — not re-verified]` | Not verified | PRIV-2 |
| Breach: CERT-In 6 h; DPDP Board + Data Principals | CERT-In Directions 2022; baseline §3 | 24 Aug 2026 | No new control; this slice adds a public write door, so ALV-249's runbook applies |

## 5. Abuse cases

| # | Actor | Does | Stopped by |
|---|---|---|---|
| AB1 | Bot with the poster photo | Posts 10,000 leads | SEC-5 (per-event and per-address caps), manual unpublish |
| AB2 | Bot | Exhausts the event's limit so the real hall is refused | SEC-5 per-address cap below the event cap |
| AB3 | Attacker | Adds `lead_owner`, `status`, `name`, `owner`, `docstatus`, `_assign` to the post | SEC-1 (refuse any key not on the form) |
| AB4 | Attacker | Puts `<img onerror>` in the comment to run script in a Sales Manager's CRM session | SEC-9 |
| AB5 | Curious attendee | Reads back their own or another's entry; probes which routes exist | SEC-2, SEC-4 |
| AB6 | Sales Manager | Clicks "grant guest link access" on User → 500 staff names public | SEC-6 |
| AB7 | Sales Manager | Builds a form asking Aadhaar or religion | PRIV-2 (D8-A gate + server refusal) |
| AB8 | Employee-only or Sales User login | Lists all leads through `/api/resource`, report view, export | SEC-10 |
| AB9 | Attendee on a shared staff phone | Next person sees last person's answers after a failed send | Accepted, setup guide (01b §7) |
| AB10 | Anyone | Sticks a fake QR over the real one (phishing) | Card prints the address in plain text (01b §6.4). Not preventable by us |
| AB11 | Departing Sales Manager | Exports the list on the last day | Allowed role; detectable only if Frappe logs the export — see worry W2 |

## 6. Security requirements

Each must trace to an acceptance criterion. "Fresh site" = a new site with CRM v1.84.0
installed, per data-doors.

**SEC-1 · The guest save writes only the form's own fields.** One `allow_guest=True`,
`methods=["POST"]` endpoint. It accepts a route and values. The set of writable fields is
**the published form's own field list, intersected with the allowed types (01b §13.4)**.
`Event form` is set on the server from the route, never from the post. Any other key in the
post → the whole save is refused (fail closed, not silently dropped). No `lead_owner`,
`status`, `owner`, `name`, `naming_series`, `_assign`, `docstatus` from a guest.
*Test:* post with each of those keys and with an unknown key → refused, no lead created;
post a valid entry → lead has only form fields set, `Event form` equals the route's form.

**SEC-2 · Nothing is read back.** Success returns a fixed body with no lead name, no echo,
no count. Errors return only a fixed code (`NOT_SENT`, `TOO_MANY`, `CLOSED`, or a
field-level validation message naming the field label). Never a traceback, never a value.
*Test:* assert the full response body for success and for each failure; assert the lead
name string does not appear in it.

**SEC-3 · One counted bypass, nowhere else.** The insert uses `ignore_permissions=True` once,
in a new file, added to `TestSec16IgnorePermissionsCeiling.CEILINGS` at **1**
(`tests/test_portal_security_010.py:731`). The page reads the Web Form through the ORM.
No Guest DocPerm is added to CRM Lead or Web Form. *Test:* the ceiling test; and on the
fresh site, `/api/resource/CRM Lead` and `frappe.client.get_list` as Guest return 403.

**SEC-4 · Only a published, clean form opens, and the check runs on the server on GET and
POST.** Unknown route, unpublished form, draft, or a form holding any banned field type
(Link, Attach, Attach Image, Text/HTML/Markdown Editor, Datetime, Time, Currency, Percent,
Color, or anything not in the allowed list) → the same closed card on GET and `CLOSED` on
POST. Identical output for "closed" and "never existed". Allowed list, not banned list:
a new Frappe field type is refused until someone adds it. *Test:* one case per banned type
plus one invented type; unpublish between GET and POST → POST refused; compare closed and
unknown responses byte for byte.

**SEC-5 · Limits that let a hall in and keep a bot small.** Reuse `field_app_limits.py`:
`_limited` keyed on the hashed route (per event, `ip_based=False`) at **1,000 an hour**, and
`_limited_by_address` at **400 an hour**. So one address cannot exhaust an event, and one
event cannot write more than 1,000 leads an hour. Numbers are mine, to be confirmed by
the OPS-9 load test (300 in 5 minutes from one address must all land). No captcha, no
honeypot until spam is measured (OPS-3). No nginx change in this slice. *Test:* read
`__alvoraa_limit__` / `__alvoraa_address_limit__` off the function and pin both; 401st
post from one address → `TOO_MANY`, answers kept (UI test).

**SEC-6 · Guest can never hold read or select on User or Employee, by structure.** A
`validate` hook on `Custom DocPerm` (and `DocPerm`, if writable on the site) refuses any row
with role `Guest` and read/select on `User`, `Employee` or `CRM Lead`. This stops
`grant_guest_link_access` (`crm/api/form.py` 268-323, per DevOps §2) on the stock page too.
**Existing rows:** before switch-on, a read-only count of Guest rows on every tenant with CRM;
any on those three doctypes is reported to Surbhi and removed only on her word.
*Test:* on the fresh site, call `grant_guest_link_access` for User as Sales Manager → refused;
insert the Custom DocPerm directly as System Manager → refused; `search_link` on User as
Guest → nothing. I chose a hook over a release-time count because a count cannot stop a
click made between releases.

**SEC-7 · The organiser box is decided on the server.** It is in the HTML only when the
session user has Sales Manager or System Manager. Page stays `no_cache = 1`.
*Test:* Guest and Sales User GETs contain no organiser-box markup, no draft flag, no QR
markup; Sales Manager GET does.

**SEC-8 · The page stays inside its own site.** No site, tenant or host parameter is read
from the request. The QR and printed address come from `frappe.utils.get_url()` of the
current site. *Test:* the endpoint and page ignore a `site` / `host` parameter; the QR
string equals `get_url()` + route.

**SEC-9 · Guest text cannot run in staff screens.** Free text is stored as plain text with
length caps on the server (Data 140, text fields 2,000 characters); the banned editor types
(SEC-4) keep HTML fields off the form. *Test:* post `<img src=x onerror=alert(1)>` and
`<script>` in the comment → stored as text; open the lead in CRM's lead page and list view
on the fresh site → shown as text, no script runs (one browser test).

**SEC-10 · CRM Lead's read doors match §3.** Enforced by CRM Lead role permissions and
CRM's assignee rule, not by our page. *Test:* the data-doors list (doors 1-6) as Guest,
Employee-only, Sales User (not assigned, then assigned) and Sales Manager on the fresh
site, including report-view export (Sales User: no export) and link search on `Event form`.
**Unknown:** whether a stock Sales User reads all leads. If yes, C1's narrow option needs a
permission change; the BA must not write the AC until the fresh-site result is in.
Fail-closed default meanwhile: assume Sales User reads all, and do not give door staff logins.

## 7. Privacy requirements

**PRIV-1 · Collect the seven standard fields and nothing else by default.** Name, mobile,
email (optional), rating, comment, two consents. No upload, no age, no address. Extra
questions only through D8-A. *Test:* the default setup in the guide creates exactly these.

**PRIV-2 · Sensitive questions (answer to Q-UX4): stronger than the guide, but small.**
Three layers, none new machinery: (1) D8-A — only a System Manager creates a question field;
(2) the setup guide rule; (3) **the page refuses to open a form** (same path as a banned type,
SEC-4) when a field's label or fieldname contains a fixed list of words: aadhaar/aadhar,
pan, passport, voter, bank, ifsc, account no, health, medical, disease, disability,
religion, caste, sexual, आधार, धर्म, जाति, स्वास्थ्य. It is a seatbelt for honest mistakes,
not a guarantee; the label can be reworded. *Test:* a field labelled "Aadhaar number" →
closed card for guests, field named in the organiser box.

**PRIV-3 · The consent record proves what was shown.** (a) "Consent: this event" is
required **on the server** (refused if not ticked), both ticks unticked by default, never
pre-set by URL. (b) The page refuses to open a form missing either consent field or with an
empty notice (description on the this-event consent). (c) Track changes is on for Web Form
(config, property setter only if not already on), so the notice text in force at a lead's
creation time can be rebuilt from the Version history. The lead's `creation` is the time of
consent. *Test:* post with consent 0 → refused; form without notice → closed; edit the
notice → a Version row holds the old text.

**PRIV-4 · Withdrawal is as easy as consent.** The notice names the organiser's contact.
A Sales Manager unticks "Consent: news" on the lead; track changes on CRM Lead records who
and when. *Test:* untick → Version row; the "news" saved view no longer lists the lead.

**PRIV-5 · Erasure removes the person, not only the row.** Deleting a CRM Lead that carries
an `Event form` also deletes its Deleted Document copy, Version rows, comments and CRM
activity rows for that lead. Custom field answers are columns on the lead, so they go with
it. Retention: default **6 months after the event** for leads without "news" consent
`[ASSUMPTION — counsel Q4]`; operated by the Sales Manager from a saved view "due for
deletion" (no scheduled job — banned until counsel sets a number and a tenant has volume).
Backups keep the data until they age out; the notice must say so `[ASSUMPTION]`.
Leads converted to a Deal leave the event rule — counsel to confirm. *Test:* delete an
event lead → zero rows for its name in CRM Lead, Deleted Document, Version, Comment.

**PRIV-6 · No personal data leaves through the page or the logs.** No Google Fonts or any
other external host in the page (OPS-13); no analytics. Values go in the POST body only,
never the query string (OPS-8). The Error Log and any traceback from the save hold no
submitted values; limiter keys are hashed (already true of `field_app_limits.py`).
*Test:* page HTML has no `http(s)://` host other than the site; force an exception in the
save and assert the Error Log row has no submitted value.

## 8. ⚠ Questions for counsel and the compliance owner

| # | ⚠ COMPLIANCE question | What it blocks | Fail-closed default meanwhile |
|---|---|---|---|
| C-1 | Minors: may an event form collect from under-18s? DPDP s.9 and Rule 10 (parental consent; in force 13 May 2027 per secondary sources). Is "for attendees aged 18 or over" in the notice enough before and after that date? | Switch-on for any school, college or family event | Notice states 18+; setup guide forbids use at events with minors |
| C-2 | Processor agreement: are we the organiser's processor, and do we need a signed DPA before the first live event (s.8(2))? | First live event | No live event without a signed agreement |
| C-3 | Retention: is 6 months after the event right, and does the backup tail need to be in the notice? | The notice wording; PRIV-5 | 6 months; nothing shown to attendees until confirmed |
| C-4 | Is a tick box on a public no-login page valid consent, and is "this event" consent the right basis (vs legitimate use)? | Switch-on (brief kill criterion) | Two unticked ticks as designed |
| C-5 | Data-principal rights for people with no login: is the organiser's email in the notice enough? | Switch-on | Notice carries the organiser's contact; Sales Manager acts |

## 9. What I did not verify, and what I would need

- **CRM v1.84.0 source** — Docker Desktop was not running, so I could not re-read
  `crm/api/form.py`, `crm_form.py`, CRM Lead's permissions or CRM's assignee rule. Every CRM
  fact here is from 01b and 07, labelled Fact by them. Need: `hrlocal-328` running.
- **Real tenant roles and existing Guest rows** — no named CRM tenant (MK1). Need: the
  tenant name and a read-only count on it (SEC-6), by DevOps, with Surbhi's word.
- **The request guard** — `data-doors.md` says `request_guard.py` strips
  `ignore_permissions` flags from requests. I found no such file in `alvoraa_portal`. Need:
  whoever owns that file to say where it lives; if it does not exist, that is a finding for
  the next platform slice, not this one.
- **Deleted Document and Version behaviour** in PRIV-5 is Inference from standard Frappe,
  not re-read on 16.35.0.
- **Section 8(2) and the Aadhaar Act** are from recall, not re-verified today.

## 10. Worries (not findings)

- **W1:** CRM assignment rules or notifications may email lead details to people the
  organiser did not intend (OPS-11). I cannot write the actor and path until the tenant's
  CRM config is known.
- **W2:** I do not know whether Frappe logs a report-view export to Access Log for CRM Lead.
  If not, C2's "every export logged" is untrue. Check on the fresh site.
- **W3:** CRM's stock `/crm-form/<route>` stays live beside our page, with its own guest
  save (10 a minute per address). SEC-6 covers its worst risk; its other behaviour is CRM as
  shipped.
- **W4:** C3 (marketing only to "news" ticks) is enforced by a saved view and a guide, not
  by structure. A Sales Manager can still email anyone. Making it structural would need code
  on CRM's email path; I do not recommend it now.

## 11. Residual risk

| Risk | Label | Owner | Accepted on |
|---|---|---|---|
| A public write door exists for as long as QR codes are printed | Intentional trade-off | Surbhi | Not yet accepted |
| Manual erasure may not be operated | Temporary debt — removed by a counsel retention number plus a measured need for a job | Surbhi / organiser | Not yet accepted |
| Sensitive-word refusal can be dodged by rewording | Acceptable simplification (D8-A is the real control) | Surbhi | Not yet accepted |
| Spam up to 1,000 leads an hour per event | Intentional trade-off | Surbhi | Not yet accepted |

## Subtract pass

Removed: a captcha and a honeypot (no spam measured); a scheduled purge job (no counsel
number yet); a separate nginx zone (OPS-4 only if the load test fails); a per-lead copy of
the notice text (Version history on Web Form does it with config); an age field (the notice
and C-1 cover it); a sensitivity-class framework (A1 is not this slice); a separate
requirement for the QR address (folded into SEC-8) and for export rights (folded into SEC-10).
