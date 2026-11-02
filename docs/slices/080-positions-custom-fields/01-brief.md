---
slice: 080-positions-custom-fields
artifact: 01-brief
author: hrms-product-manager
date: 2026-11-02
status: draft — framing a decision for Surbhi. No design, no spec, no implementation.
inputs:
  - Surbhi's words, 2 Nov 2026 (two messages, quoted in §1)
  - hrms/hrms/alvoraa_org_structure/people_fields.py (read in full, 2 Nov 2026)
  - alvoraa_portal/.../{positions_profile,my_profile,joiner_public,people_settings,staff_api,employee_field_rights}.py (read, 2 Nov 2026)
  - hrms/hrms/alvoraa_org_structure/settings.py (read at the setter)
  - docs/slices/078-positions-faces/{01-product-brief,01c-security-privacy-requirements}.md
  - .claude/context/{product-context,no-over-engineering}.md
  - Workday, Keka, greytHR, Zoho vendor documentation read 2 Nov 2026 (cited inline)
missing_inputs:
  - 01a-ux-opportunities.md — not written for this slice
  - 07-devops-inputs.md §1 — not written for this slice
  - .claude/context/data-doors.md — DOES NOT EXIST in this repo (see §11)
---

# 080 · Custom fields on the people surfaces — a decision brief

> **This is not a build-ready brief, on purpose.** The UX scan and the DevOps first look
> do not exist for this slice, and my instructions were to frame the decision, not to
> design anything. Nothing below should go to the UX designer or the analyst until
> Surbhi has answered §9.

---

## 0 · The answer first

**Bad news first: the example you gave is already refused on purpose, and the thing you
asked for would remove the control that slice 078's whole privacy position rests on.**

`cell_number` — labelled "Mobile" — sits on the `NEVER` deny list under the comment
*"home and next of kin are the employee's to give, never a reader's to browse."* An
**alternative phone number is the same class of data**: a personal contact number. So
"such as alternative phone number" is not a gap in the list. It is the list doing its
job. (**Confirmed** — `people_fields.py:99`.)

**And your request contains two different things, which are very different sizes.** I set
them out in §2. My recommendation is a **third, smaller option**: add the **one work
field the code has already flagged twice as missing and already called a decision for
you** — a work phone / extension — as a named entry on the closed list. That is a day of
work, it changes no control, and it may well be what you actually wanted. Then decide
the architecture question separately, with evidence, rather than as a side effect of a
phone number.

**The market does not settle this the way it first appears.** Workday, Keka and greytHR
all let an administrator expose chosen fields to colleagues — **but every one of them
gates it on a permission object we do not have.** Copying the market standard means
building that missing layer, not deleting our list. §3.

---

## 1 · What you asked for, verbatim

> "Regarding Positions field, I wish that there should be built with the flexibility to
> Administrator to create custom fields in employee profile and should be able to select
> them to show on positions page, such as alternative pone number."

Then, widening it:

> "and same for profile and other place whever applicable"

**What the code does today** (all **Confirmed**, read 2 Nov 2026):

| Thing | Today |
|---|---|
| What a Positions reader may be shown | A **closed tuple of ten work facts** — `POSITIONS_PROFILE_FIELDS`. Nothing else, ever |
| What an employee may change about themselves | A **closed tuple of six personal details** — `MY_PROFILE_WRITE_FIELDS` |
| How it is enforced | An allow-list **applied twice**: the setter refuses an off-list name, and **every reader intersects again**, so a value written straight into `DefaultValue` by any other route produces nothing |
| Why not a Frappe permission level | The file says it plainly: `employee_field_rights.py` locked **write** on 35 Employee fields and **left read open** on purpose, and **HR Manager holds read at level 1 anyway** — and HR Manager *is* the Positions audience at DTC. **A permlevel cannot refuse a read here.** The allow-list is the control |
| A second, named deny list | `NEVER` + `is_denied()`, by **fieldname**, plus every field a live payroll rule set names |
| Is there a custom-field precedent? | Yes. `pan_number`, `esi_number`, `provident_fund_account` **are** custom fields created by `hrms/regional/india/setup.py`, and `NEVER` names them anyway because they may or may not exist on a tenant |

**The one fact that decides most of this brief.** The deny list is **by fieldname**. An
Administrator-created custom field has an arbitrary name. `NEVER` would not catch
`custom_aadhaar_no`, `custom_ctc_2026` or `custom_disciplinary_note`.

And it is worse than "the deny list misses it". There is already a hook,
`lock_new_custom_field` (`employee_field_rights.py:217-230`), that fires when a Custom
Field is added to Employee — **but it only assigns a permission level when the new
field's name matches a known list.** `custom_alt_phone` matches nothing, so
`level = 0`, so the field ships **readable by everyone and writable by the employee**,
with no human having made that choice. (**Confirmed in code.**)

---

## 2 · The two readings of your request — which should you be choosing?

| | **Reading 1 · a policy change** | **Reading 2 · an architectural change** |
|---|---|---|
| The question | May a personal contact number appear on the Positions page at all? | May an Administrator put **any field they create** onto a colleague-visible page? |
| Size | **Small.** One or two names added to one closed tuple, with a `Version` row | **Large.** The closed list stops being closed |
| Needs custom fields? | **No.** `cell_number` and `emergency_phone_number` already exist on Employee | Yes, by definition |
| What it costs | A deliberate privacy decision, made once, reviewable, testable | The control that 078 and 079 were both signed off on |
| What a test can still assert afterwards | The exact contents of the list | Nothing about contents. Only that *some* gate ran |

**You may want 1 and have described 2.** The phrase "such as alternative phone number"
points hard at Reading 1 — you wanted a specific missing field, and "let the
Administrator add fields" was your proposed mechanism for getting it. I cannot tell from
your words which you meant, and the difference is roughly a day against roughly a month
plus a permission layer. §9-Q1 is that question.

### 2a · "Wherever applicable" — my judgement, shown

Four surfaces use this mechanism. **Several surfaces that read employee fields do not**,
and for those "same for other places" is a different and wider piece of work.

| Surface | Uses `allowed()`? | Audience | In scope? |
|---|---|---|---|
| Positions mini profile (`positions_profile.py:68`) | **Yes**, `alvoraa_positions_profile_fields` | Positions readers — **HR Manager at DTC**, scoped by company/branch | **Yes.** This is what you asked about |
| My Profile (`my_profile.py:59,80`) | **Yes**, `alvoraa_my_profile_fields` + required | The employee, on **their own** record | **Yes — but it is a different question.** This is a **write** path |
| Joiner form (`joiner_public.py:168`) | **Yes**, `alvoraa_joiner_fields` + required | **A person who is not yet an employee**, reaching a guest endpoint with a token | **Yes, and it is the riskiest of the three** |
| The settings card (`people_settings.py:88-131`) | **Yes** — it is the setter and the preview | System Manager only | **Yes.** Whatever you choose is configured here |
| **Staff directory** (`staff_api.py:59-83`) | **No.** Its own hard-coded `ROW_FIELDS` tuple | **Every employee, their whole company** (`DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"`) | **No — and deliberately not.** See below |
| Team pages, Home, Goals, Time screens, HR people list | **No.** Each has its own field list | Varies | **No.** Not governed by these keys |

**Why I am keeping the staff directory out, even though it is the obvious "other
place".** Its audience is roughly **80× wider** than Positions' — every employee in the
company, not a handful of HR logins. And its own code already records that you decided
its contents personally on 24 Sep 2026 (work contact in, *"the companies have NDAs"*),
with a standing note: *"Adding a field here is a visibility change and needs its own
decision."* Putting administrator-chosen fields on that surface is the single largest
privacy move available in this product. It should be its own decision with its own
security review, not a consequence of this one. **Flagged as §9-Q4, not folded in.**

### 2b · The three keys ranked by risk — they should almost certainly not be one switch

This ranking is counter-intuitive and it is the most important paragraph in the brief.

| Rank | Key | Why it sits there |
|---|---|---|
| **1 · highest** | `alvoraa_joiner_fields` / `..._required` | A **person who is not yet employed**, holding the least trust in the whole system, reaching a **public endpoint**, being asked for a field nobody vetted. There is no employment relationship to rely on as a lawful basis — 078's own read says it is almost certainly notice-and-consent. Asking a stranger for `custom_aadhaar_no` through a forwarded link is the worst outcome in this document |
| **2** | `alvoraa_my_profile_fields` | A **write** path. The file states the rule it protects: *"a self-service screen must not become a way round field rights"*, with pay, bank and identity numbers named. And the guard that would normally stop it, `refuse_own_locked_change`, **works off permission levels** — and a new custom field ships at **level 0** (§1). So a custom field on this list is a field the employee can **write to their own personnel record**, by default, with nobody having decided that |
| **3 · lowest** | `alvoraa_positions_profile_fields` | **Read only**, to a **narrow, scoped** audience who at DTC already hold plain read on Employee in Desk. It is a faster door, not usually a new disclosure. This is the one you asked about, and it is the safest of the three |

**And the consequence you must not discover later.** The three joiner and My-Profile keys
all point at `MY_PROFILE_WRITE_FIELDS` **by identity, not by copy** — a deliberate choice
(079 AC-104) so that a third candidate list cannot appear and drift away from what the
code actually allows. **If custom fields become tickable for My Profile, the joiner form
inherits them for free**, unless somebody decides otherwise. That means the cheapest
version of Reading 2 hands your newest, least-vetted field straight to your
least-trusted principal. I am naming it, not designing around it: breaking the
by-identity link to dodge this is itself a decision with a cost (two lists that can
drift), and it is yours, not mine.

---

## 3 · The competitive frame — and it does not say what it looks like it says

The useful question was: *if the market standard is "admin picks any field", Reading 2 is
table stakes, not reckless.* Here is the honest answer.

| Product | What an administrator can expose on a colleague-facing profile / chart | Evidence |
|---|---|---|
| **Workday** | Custom objects and fields appear on a profile's **Additional Data** tab. Org-chart cards are configured per business object. **But:** the tab *"only displays the custom objects and custom fields for which you have View permissions on the domain security policy that secures the custom objects"*, and where a user lacks access the chart shows **blank lines**. Contact information is designated **public or private per type**, and workers can set their own **Change Public Profile Preferences** | **read, 2 Nov 2026** — doc.workday.com admin guide (custom objects and labels; organization charts; contact information) |
| **Keka** | Admins **customise a card** and set a profile field's visibility, including **Hidden for Everyone**. Documented as a privacy control. Whether a middle setting exists (e.g. managers only) is **not documented** | **read, 2 Nov 2026** — help.keka.com art. 39946688026385 |
| **greytHR** | An **Employee Directory Config** page in System Settings chooses which employee details appear in the employee and team directories. A **Private** toggle restricting a field to internal users is documented — but for *recruitment* category fields, not general custom fields. greytHR's own help **tells admins to contact support before changing these settings** | **read, 2 Nov 2026** — greythr.com help-admin (employee directory config; recruit custom fields) |
| **Zoho People** | **Could not confirm.** I searched and found only Zoho **Payroll** custom-module and "Display in Portal" documentation, which is a different product surface. 078's brief already recorded a Zoho community thread where an admin *"could not predict the result"* of their own visibility settings | **not verified** — do not quote |
| **SAP SuccessFactors / Darwinbox** | `[recall — verify]` Both are generally understood to offer role-based permission on custom profile portlets. **I did not verify either and no claim here should be relied on** | `[recall — verify]` |
| **Frappe HR standard** | A Custom Field on Employee has a **permission level**, and Desk honours it. There is no concept of "show this on an org-chart card" at all | **Confirmed** from this repo |
| **Us today** | Ten work facts, closed, from a server constant | **Confirmed** |

**What the market actually shows — and it is the opposite of the first impression.**
Every vendor who lets an admin expose a custom field gates it on **a permission object
that can refuse a read**: Workday's domain security policy, Keka's per-field visibility,
greytHR's directory config. The freedom is real; **it is never unconditional.**

**We are the one product in this table that cannot refuse a read.** That is not an
oversight — `people_fields.py` explains why: read was deliberately left open at level 0
so no existing screen lost a field, and HR Manager holds read at level 1 regardless. So
**"let the Administrator pick any field" is table stakes only in a product that has the
permission layer underneath it.** In ours, Reading 2 is not "catch up with Workday". It
is "ship Workday's freedom without Workday's gate".

**What we will deliberately not do that they all do, and why it is better for our user.**
greytHR's own documentation tells administrators to **ring support before touching the
directory config**. Zoho's users cannot predict their own settings. We offer a short
curated list with a **preview of what a reader actually sees** — 078's one genuinely
Attractive feature. A free pick over every field destroys that preview's value, because
nobody can preview a field whose meaning only the person who created it knows.

---

## 4 · Who wants this, and why

| Persona | What they want here | My read |
|---|---|---|
| **HR Manager** | To see one more useful work fact when they open a mini profile — most plausibly **how to reach this person at work**, which is the gap `staff_api.py:70-74` already names | Genuine, and Reading 1 serves it |
| **CXO / Administrator** (you) | Not to have to ask engineering every time a field is missing | Genuine, and it is the real motive behind Reading 2. Worth saying out loud: **the cost you are trying to avoid is a conversation with us.** A middle option that pre-answers the common case may remove the irritation without the architecture |
| **Employee** | **Nothing. They are the data subject here, not the beneficiary.** This feature is about other people seeing *their* details. On My Profile they gain a write they did not ask for; on Positions they gain visibility they cannot see and cannot audit — 078's `01c` already records that *"the employee whose face and documents are on the Positions page cannot open that page"* | This is the asymmetry product-context §2 tells us to look at hardest: *"a slice that improves the manager's convenience by degrading the employee's experience has failed, whatever the adoption number says."* Reading 2, unguarded, is exactly that slice |

**No demand evidence exists.** No customer request, demo note, support ticket or
lost-deal note for this. The request originates with you. **Evidence required**, and it
is why §5 is a proxy.

---

## 5 · Kano class — **proxy**, no survey

| Candidate | Class (proxy) | Why |
|---|---|---|
| A **work contact field** on the Positions profile and the directory (Reading 1, narrowed) | **Must-be** | Every competitor's directory carries a work contact. Our own code names its absence twice. Nobody will praise it; its absence quietly makes the page less useful |
| **Admin picks any custom field** for a colleague-visible page (Reading 2) | **Performance** for the buyer, **Reverse for the employee** | Buyers compare configurability, so it is Performance in a demo. But a feature that lets one person decide what colleagues learn about another, with no route for the subject to see or object, is **Reverse by definition** — some people actively do not want it. Both classes are true of the same feature, for different people, which is itself the finding |
| A **preview of what a reader sees** (already built, 078) | **Attractive** | Nobody documented doing it; greytHR tells admins to ring support instead |

**What would change this:** ask the next three demo prospects the two-question Kano pair
on *"an administrator can choose which extra employee fields colleagues see"* — and ask
the **dysfunctional** question of an employee, not only a buyer. Five answers would beat
everything above.

---

## 6 · The named user outcome, and how we would know

**One outcome, one person.** *Pritam, HR Manager at DTC, opens a mini profile from the
Positions table and can see how to reach that person at work — without asking anybody and
without opening Desk.*

That sentence is satisfiable by Reading 1. It is **not** made more satisfiable by Reading
2; Reading 2 only makes it satisfiable by somebody other than us.

| Measure | Baseline | Target | How |
|---|---|---|---|
| Mini profiles where the reader got the contact they came for | baseline unknown — measure first | Ask Pritam after two weeks. One question, not a dashboard | A conversation, recorded in the slice folder |
| Requests to engineering for "please add field X to the Positions page" | **baseline unknown — measure first, and this is the number that decides Reading 2.** I have exactly one data point: this message | Fewer than one a quarter after Reading 1 ships | Count them in ALV |
| Fields visible to a reader that the tenant did not deliberately choose | **0 today** (closed list, tested) | **Still 0** | The existing tests in `test_my_photo_078.py` and `test_mini_profile_078.py` assert the tuples exactly |
| Employee-written fields on their own personnel record that nobody vetted | **0 today** | **Still 0** | A test, not a dashboard |

Rows 3 and 4 are **Kano-must**: if either moves off zero, this slice caused a breach,
not a feature.

---

## 7 · My recommendation, and the ladder

**I recommend a third option, and I recommend not deciding Reading 2 this week.**

### 7a · Recommended: one named work field, on the closed list

The code has already asked you this question twice and nobody answered it:

- `people_fields.py:40-42` — *"Work phone is deliberately absent: Employee has no such
  field… `cell_number` is labelled 'Mobile' and is personal, so it is not a substitute.
  Ten, not eleven."*
- `staff_api.py:70-74` — *"There is **no work phone or extension field at all**… Adding
  a work-phone field is a decision for Surbhi, not a thing to slip in here."*

So: **add one custom field to Employee for a work telephone or extension, name it on
`POSITIONS_PROFILE_FIELDS` as the eleventh entry, and nothing else changes.** It is a
**work fact**, so it belongs on that list on the same principle as `company_email`. The
list stays closed. The deny list stays by-fieldname and stays complete. Every existing
test still asserts an exact tuple. No permission layer is needed, because a work phone is
not sensitive.

**Ladder rung: 3 · customisation** (one Custom Field, created by us in code the way the
India regional pack already does) **plus rung 4 for one line** (its name on the tuple).

Cheaper rungs rejected, by name:
- **Rung 1, already there:** rejected. ERPNext's Employee genuinely has no work-phone
  field. Verified twice independently in this codebase.
- **Rung 2, configuration:** rejected for this field — there is nothing to configure
  until the field exists. *Accepted for everything else:* the tick itself is already
  configuration, through the existing System-Manager-only setter with its `Version` row.
- **Rung 5, a new DocType / rung 6, a new app:** not proposed by anyone.

**And if your "alternative phone number" really did mean a second *personal* mobile:**
that is Reading 1 proper, and my recommendation is **no** for the Positions page — it is
`NEVER` data for a reason, and HR already has it in Desk. The place a second personal
number legitimately belongs is **My Profile, as a field the employee maintains
themselves**, and even that is a decision, not an obvious yes. §9-Q2.

### 7b · On Reading 2, my recommendation is "not yet", and the condition

I am not saying never. I am saying **the evidence for it is one message, and the price is
the control two shipped slices were signed off on.** My recommendation:

1. Ship 7a.
2. **Count the requests.** Every time anyone asks for a field that is not on the list,
   log it in ALV with the field name and who wanted it.
3. **Revisit when there are five, with their names in front of us.** If those five turn
   out to be work facts, the answer is "extend the closed list to thirteen" and we will
   have spent nothing. If they turn out to be genuinely tenant-specific (a plant code, a
   union local, a route number), **then** Reading 2 has earned a design — and at that
   point the design question is the one the market already answered: *what is our
   permission object?*

This is not "phase 2 will fix it". 7a is complete on its own and needs nothing after it.
Step 3 is a **separate decision with an evidence trigger**, which is the opposite of a
phased plan.

### 7c · If you choose Reading 2 anyway — the honest costs, so you choose with them

Not a design. Just the bill, so "yes" is informed:

- The deny list stops being able to work. It is by fieldname; you are introducing
  arbitrary fieldnames. Something else has to decide, and that something does not exist.
- `lock_new_custom_field` assigns **level 0** to any name it does not recognise (§1). So
  on current behaviour a new custom field is readable by all and writable by the
  employee, by default.
- **Three switches, not one**, on the §2b ranking — and a decision about the
  by-identity joiner link that currently makes a third list impossible.
- The preview feature loses most of its value (§3).
- Security and privacy review becomes the gate, not a step: this is a new
  purpose-limitation question per field, forever (§8).
- `[ASSUMPTION]` Roughly a month of work including the permission layer, review and
  tests. **I have not had this costed and I am not the right person to cost it** — the
  engineer and DevOps would price it at a strategy gate. Treat the number as
  `Needs validation`.

---

## 8 · Regulatory read — four lines

1. **Which regime.** India's **DPDP Act 2023** (Rules notified 14 Nov 2025, duties phased
   to roughly May 2027). No AI regime is engaged and nothing here may create a path to
   one.
2. **Whose obligation.** Our **customer's** — the employer is the Data Fiduciary for its
   employees. 7a helps them discharge it (a short, curated, previewable list). Reading 2
   **transfers a compliance decision to whoever happens to be Administrator that day**,
   with no record that a decision was made. That is the version a security reviewer will
   push back on, and the sales gate in this market is the security review
   (product-context §9). *I am not a lawyer.*
3. **What becomes newly possible.** 7a: one work fact on one scoped screen. Reading 2:
   **an open-ended set of personal data fields, chosen after the review, on surfaces the
   subject cannot see** — and on the joiner form, collected from a person with no
   employment relationship.
4. **The honest downside.** 7a I would defend on a front page without hesitation.
   **Reading 2 as asked I would not** — "our customer's administrator put a field called
   `custom_disciplinary_note` on a page 597 colleagues could read, and nothing in our
   product noticed" is a sentence this team has already lived through once, as ALV-249.

**Refusals, written down so they cannot arrive later.** Nothing in this slice, in any
reading, may put pay, bank, statutory identity, health, date of birth, home address,
next-of-kin or a performance or disciplinary note on a colleague-visible surface. No
custom field may become a route round `employee_field_rights`. No field added here may
reach a model prompt or an automated decision.

---

## 9 · What needs your decision

**Must know — these block starting.**

| # | Question | My recommended assumption if you want us to keep moving | Blocks |
|---|---|---|---|
| **Q1** | **Reading 1 or Reading 2?** Did you want *a missing field*, or *the power to add fields*? | **Reading 1, served by 7a**: one work-phone field on the closed list. Count requests before deciding Reading 2 | Everything |
| **Q2** | **Did "alternative phone number" mean a second *work* number, or a second *personal* mobile?** They get opposite answers from me | **Work.** If personal, my answer is no for Positions and "let us discuss" for My Profile | The field's definition and whether 7a is right at all |
| **Q3** | If Reading 2: **one switch or three?** Positions read, My Profile write, and the joiner form are not the same risk (§2b), and the joiner currently inherits My Profile **by identity** | **Three separate decisions, and the joiner form gets none of it** | The whole shape of the work |
| **Q4** | **Does "wherever applicable" include the staff directory** — every employee, company-wide (§2a)? | **No.** It is a separate decision with a separate review, and your own 24 Sep 2026 decision governs that list | Whether this is one slice or two |

**Should know.**

| # | Question | Owner |
|---|---|---|
| Q5 | How many times has a field actually been missing? I have one data point and it is this message | Surbhi / ALV |
| Q6 | If a work-phone field is added, should it also go on the **staff directory** row list, where it is arguably more useful? That is Q4 in miniature and the answer may be yes even if Q4 is no | Surbhi |
| Q7 | Is the Administrator at a tenant **ever the customer**, or always us? If always us, Reading 2's whole premise changes — the irritation it removes is our own process, not a customer's | Surbhi |

---

## 10 · What this hands to the security engineer

Named, **not answered by me.** These are the questions a security and privacy review has
to answer before Reading 2 could be built, and they are the reason I am recommending
against it for now.

1. **An arbitrary fieldname defeats a name-based deny list.** `NEVER` and `is_denied()`
   match fieldnames. `custom_aadhaar_no`, `custom_ctc_2026` and
   `custom_disciplinary_note` match nothing. What replaces a name match — a fieldtype
   rule, a label scan, a per-field classification the Administrator must set, a
   human approval step? And whatever it is: **what refuses a read**, given that
   `people_fields.py` states a permlevel cannot?
2. **A custom field has no permission level assigned by anyone who thought about it.**
   `lock_new_custom_field` (`employee_field_rights.py:217-230`) assigns a level only when
   the fieldname is on a known list; anything else gets **level 0** — read by all, written
   by the employee. Is that acceptable as a default, and if not, what is the fail-closed
   default for a field nobody has classified?
3. **DPDP purpose limitation across a change of purpose.** A field collected for one
   reason (say, a plant code for a payroll rule) and later **displayed for another** (on a
   colleague-visible profile) is a new purpose for data already held. Does the existing
   notice cover it? Does the subject need to be told? Who records that the purpose
   changed, and when?
4. **The joiner form inherits My Profile by identity** (079 AC-104). If custom fields
   become tickable for My Profile, they reach a **guest-reachable form answered by a
   non-employee** unless something stops them. Is the by-identity link the control, or
   does it become the hole?
5. **The write path round field rights.** `people_fields.py:60-62` says *"a self-service
   screen must not become a way round field rights."* A level-0 custom field on
   `MY_PROFILE_WRITE_FIELDS` is exactly that route. What enforces the rule when the
   permission level cannot?
6. **Testability.** Today a test asserts an exact tuple, and CI fails on anything else. If
   the list is open, **what is the assertion that replaces it?** A control nobody can
   write a test for is not a control.
7. **`data-doors.md` does not exist in this repo.** My instructions require me to read it
   and answer its five "For Surbhi" questions. I could not: `.claude/context/` has
   thirteen files and that is not one of them (**Confirmed**, 2 Nov 2026). I have answered
   the access questions I can at product level in §2a, §2b and §4, but **the file's own
   five questions are unanswered and I am not able to invent them.** Either the file needs
   writing or the instruction needs correcting — raising it rather than passing it on
   silently.

---

## 11 · Subtract pass — what I removed

Read back once, asking only *what can I delete and still meet the requirement?*

- **A design for how an Administrator would pick fields.** Removed. I was asked to frame
  the decision; a design would presuppose its answer.
- **A "field classification" scheme of my own** — sensitivity tags on custom fields, an
  approval workflow for a new field, an audit screen of who exposed what. Removed, all
  three. They are Reading 2's design, they are the security engineer's to shape
  (§10), and sketching them would make Reading 2 look cheaper than it is.
- **A proposal to extend the Positions list from ten to thirteen** (work phone, extension,
  seat/location) while we were in there. Removed. **One field, one outcome.** The other
  two have no named person asking for them.
- **The staff directory.** Removed from scope, flagged as Q4/Q6 instead (§2a).
- **A migration or back-fill for the new work-phone field.** Removed. An empty field that
  HR fills in as they go is fine; nobody asked for 442 numbers on day one.
- **A second settings card, a new DocType to hold field choices, a feature flag to turn
  Reading 2 on per tenant.** Removed, none asked for, all on the banned list.
- **My own first instinct: recommend Reading 2 with guard rails, because it is the more
  impressive answer.** Removed, and this is the removal that mattered. It would have been
  a month of work, a new permission layer and a weakened privacy position, to serve one
  message and one phone number.

---

## Open questions

See §9. Q1–Q4 are **must know** and block starting. Q5–Q7 are **should know**.
§10 item 7 (`data-doors.md` missing) has no owner yet and should get one.

## Assumptions

- `[ASSUMPTION]` Your "alternative phone number" example is representative of the kind of
  field you have in mind, rather than the only one. If you have three more in mind, say
  what they are — it would move Q1 faster than any argument in this brief.
- `[ASSUMPTION]` The Administrator at a tenant is us, not the customer. If customers hold
  Administrator, Reading 2 is materially more dangerous than §7c says. Q7.
- `[ASSUMPTION]` Roughly a month for Reading 2 including the permission layer. **Not
  costed by an engineer.** `Needs validation`.
- `[ASSUMPTION]` No customer has asked for configurable profile fields in writing. A demo
  note or ticket would change §5 from proxy to evidenced.
- `[ASSUMPTION]` A work telephone or extension is useful to DTC at all. DTC's staff are
  largely shop-floor and field workers who may have no work number — in which case 7a is
  a field nobody fills in, and the real answer to Q2 is "personal mobile", which I am
  recommending against. **This is the weakest assumption in the brief** and the fastest
  one for you to check.
- `[ASSUMPTION]` SAP SuccessFactors and Darwinbox offer role-based permission on custom
  profile portlets. `[recall — verify]`, not relied on anywhere in my recommendation.

## Kill criteria

- **Kill 7a** if DTC has no work telephone numbers to put in it. Ask one question before
  anything is built.
- **Kill Reading 2** if the security review cannot name a mechanism that refuses a read
  (§10 item 1), because then the feature ships a control that does not control anything.
- **Kill this whole slice** if the answer to Q1 is "I only ever wanted the phone number" —
  then it is a one-line change on an existing slice, not a slice of its own, and should be
  an ALV ticket instead of a folder.
