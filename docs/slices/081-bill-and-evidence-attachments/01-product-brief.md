# Slice 081 — A bill on an expense claim, evidence on a regularization

**Product brief · 3 November 2026 · Status: DRAFT for Surbhi's gate**
Requirement, in her words: *"we need to add the attachment field in attendance
regularization request and expenses claim."*
Decision already given: *"make it mandatory"* → revised to **mandatory on the expense
claim, optional on the attendance request.**

**Settled since the first draft (do not re-open):** **1 MB** for an image, **3 MB** for a
PDF · **no** HR-configurable rules, one fixed behaviour · **DTC asked for this** — a named
customer requirement, not a guess · **a sensitive claim type routes to an approver ROLE,
per company, so a manager never opens a medical receipt** · HR already adds their own
expense types — no work · **Desk is not exempt**: the rule fires at submit there, and
where no bill exists HR attaches a signed self-declaration · **on regularizations, a
plain line saying the manager will see the file — a warning is fair when the person has a
choice, and there the attachment stays optional.** See §1.4, §2, §3, §3.1a, §3.2, §3.3
and §3.4.

**⚠ One part of this slice carries real design risk and must not be waved through at the
design gate: the approver role (§3.3).** It changes a standard Frappe approval flow.
Everything else is reuse.

---

## 0 · Two things to read first

**Bad news first: two inputs this brief is supposed to stand on do not exist.** There is
no `01a-ux-opportunities.md` (the UX designer's scan) and no `07-devops-inputs.md` §1
(what this would add to run) for slice 081. **Confirmed** — the folder is new. So:

- the competitor table below is **my product read, not a benchmarked UX scan**;
- the run-cost and storage lines are **marked `evidence required`**, not estimates I
  am asking anyone to trust.

My recommendation: the design gate runs after those two arrive. Nothing in the brief
needs to change for them, but the storage number might change the file rules.

**The other thing.** Half of the coordinating hypothesis behind this slice is wrong, and
it is worth saying plainly before the table: **there is no `allow_attachments` setting to
tick any more.** See §1.

---

## 1 · Current state — checked against the repo, not recalled

### 1.1 Desk already accepts attachments on both. There is nothing to configure.

| Fact | Label | Where I checked |
|---|---|---|
| `allow_attachments` **no longer exists as a DocType field in Frappe.** The attachments sidebar shows on any **saved** document when the user has `write` and `max_attachments` is not reached — `.toggle(!max_reached && this.frm.has_perm("write"))` | **Confirmed** | `frappe/public/js/frappe/form/sidebar/attachments.js`, and the field is absent from `frappe/core/doctype/doctype/doctype.json` |
| Our stack is newer than that, so the rule holds | **Confirmed** | `hrms/pyproject.toml` → `frappe = ">=17.0.0-dev,<18.0.0"` |
| The string `allow_attachments` appears **nowhere** in this repo | **Confirmed** | grep, whole worktree |
| Neither `Expense Claim` nor `Attendance Request` has an `Attach` field of its own. In all of `hrms/hr/doctype` only Travel Request, Job Applicant, Employee Referral and Appraisal do | **Confirmed** | grep `"fieldtype": "Attach` |

**So the cheap rung everyone hopes for — "tick a box" — is not available, because the box
is gone and the behaviour is already on.** An HR person working in Desk can attach a bill
to an Expense Claim today, and an attendance request too. Nothing in this slice is for them.

### 1.2 On the surface staff actually use, neither form can carry a file. Both halves are real work.

| Surface | Expense claim | Attendance regularization |
|---|---|---|
| **ESS portal form** (the PWA — this is the phone) | Modal has Type, Date, Amount, Description. **No file input.** `request-modals.html` L65–99 | Form has a reason dropdown and a free-text box. **No file input.** `portal.js` `acForm()` L6141 |
| **Server endpoint** | `hr_api.apply_expense_claim(expense_type, expense_date, amount, description)` — **no file parameter** L2395 | `attendance_correction.raise_correction(...)` and `raise_for_report(...)` — reason and explanation only, L979 |
| **Employee's own list afterwards** | name, date, status, amount. No file link. `portal.js` L9948 | reason, dates, state, HR's note. No file link. `acReqCard` L6233 |
| **The reviewer's queue in the portal** | approver sees name, employee_name, expense_type, expense_date, amount, note, waiting_since — **no file** `inbox_api._part_expense_approvals` L581–609 | HR queue shows the request fields only; `REQUEST_FIELDS` L890 has no file |
| **Field app (driver / check-in PWA)** | not present — the field app is check-in, codes, punches and notices only (`field_app_records.py`) | not present |

**Confirmed, and it is the point of this slice:** today a bill reaches the approver by
WhatsApp or not at all. And **even if a file existed, no reviewing screen in the portal
would show it.** An attachment an employee can upload but a reviewer cannot see is not a
feature, so both ends ship together or neither does.

**Correcting my own brief:** I expected "expense = configuration, attendance = code".
It is **code on both**, and *less* code than I expected, because the pieces to reuse all
exist. The honest difference between the two halves is now **behaviour, not plumbing:**
**the expense claim enforces, the attendance request invites.**

### 1.3 What already exists to reuse (so this is small)

| Need | Already in the product | Label |
|---|---|---|
| Upload from a phone | `uploadMyDocument` → `/api/method/upload_file` with `is_private=1`, then a small whitelisted endpoint records the url. `portal.js` L5122 + `hr_api.attach_my_document` L3948 | **Confirmed** |
| Show a file without handing out its URL | `employee_documents_read.open_employee_document` — guard, then stream the bytes; the browser never receives a `/private/files/...` address | **Confirmed** |
| Record who looked | `Alvoraa Photo Access Log` already has a `source` Select, and its own description says a third kind of looking is *"a WHERE clause, not a redesign"* | **Confirmed** |
| Strip a photo's hidden data and shrink it | `employee_photo.py` — one Pillow call, resize + strip, with a 5 MB ceiling | **Confirmed** |
| Per-user rate limit | `field_app_limits._limited` | **Confirmed** |
| A per-file ceiling | `max_file_size` — slice 078 chose **5 MB** and deliberately never applied it ("a per-site setting, Surbhi's word at release"). **Superseded for this slice: Surbhi's figure is 1 MB.** See §3.2 | **Confirmed · evidence required:** is anything set on dev and production today? |

**Rung on the ladder: 4 — new code.** Rejected below it: *already there* (true on Desk,
false on the portal, and the portal is where staff are); *configuration* (no setting
exists); *customisation* (a Custom Field or Client Script cannot add a file control to a
hand-written portal page, and a Property Setter has nothing to set). **Not** rung 5 or 6:
no new DocType, no new app. The file is a standard Frappe `File` row attached to the
document — which means **the HR person on Desk sees the same file in the sidebar for free.**

**One part of the slice sits a rung lower: the routing in §3.3 is rung 3 —
customisation.** It is one Custom Field on an existing child table, read by a query that
already runs.

### 1.4 "Let the administrator add expense types" — already delivered, no work

Surbhi, 3 November 2026: *"we need to allow the administrator to add expense types
themselves according to the organisation context."* **This already works. Recording it
here so nobody builds it twice.**

**Confirmed:** `hr_api.get_expense_types()` (L2348) does a live
`frappe.get_all("Expense Claim Type")` on every call, so a type HR creates in Desk
appears on the employee's portal form at once. No list in our code, nothing to deploy.

**The one real-world catch, and it is documentation, not code.** A new type also needs a
**default account per company**, or the claim cannot book to the ledger. The product
already refuses this at filing with a message naming exactly what HR must set — *"the
expense type {0} has no expense account for {1}. Please ask HR to set one on the Expense
Claim Type"* (`_expense_claim_accounts`, L2383–2389, ALV-178). So the honest statement
is: **setting up a new expense type is a two-step job for HR — create the type, then set
its account for each company.** That belongs in the release note and the HR
documentation. **No code in this slice.**

---

## 2 · Job to be done

> *"As a driver at DTC, when I pay Rs 420 for diesel out of my own pocket, I want to
> photograph the bill while I am still standing at the pump, so my supervisor can
> approve it the same day instead of asking me for the paper next week."*

Persona: **Employee**, and specifically the **frontline employee on a cheap Android
phone** — the one product-context §2 says wins any design trade-off.

- **Line manager / expense approver:** gains the one thing that makes a claim decidable
  in a single tap. Today they either trust the amount or chase the paper.
- **HR Manager:** gains fewer "please send me the bill" messages, and a claim that still
  has its evidence attached three months later at audit.
- **CXO:** no change. Summaries only.

**Current pain — and this is a named customer requirement, not a guess. Confirmed by
Surbhi, 3 November 2026:**

> *"they shared the requirement and also asked for these amendments to make it worth
> their usage."*

So the footing is this: **DTC files expense claims today, DTC asked for the attachment,
and DTC's own words are that the amendment is what makes the expense module worth using.**
That removes the "this may have no users yet" caveat entirely and raises the priority —
it is a Must-be gap with a live customer behind it, not a feature we are offering.

The story underneath it: the portal's claim form has never had a file control, so every
claim ever filed through it reached its approver as a number and a sentence, and the bill
travelled by WhatsApp or not at all.

`evidence required` (useful, not blocking): how many claims DTC filed in October, and how
many were queried for want of a bill. It sharpens the §12 baseline; it no longer decides
whether to build.

---

## 3 · The two behaviours, said plainly

| | Expense claim | Attendance regularization |
|---|---|---|
| Attachment | **Mandatory** | **Optional** |
| What the server does with no file | **Refuses, and says why in words** | Accepts, saves, says nothing |
| What the form says | "Photo of the bill · required" | "Add a photo or document if you have one" **plus, before they choose a file: "your manager will see anything you attach here"** (§3.4) |
| Why | A claim moves money. A bill is the thing that justifies it | There is no document for *"the biometric did not read my thumb."* A hard rule would be a dead end for the commonest real case |

**Where the rule lives (this is not negotiable).** The refusal is **on the server**. The
form hiding its own button is convenience on top. The standing lesson in this product is
exactly this: **test what the form sends, not just what it draws** — so the acceptance
criteria must include a test that posts a claim with no file and asserts the server's own
refusal, and that the refusal reaches the screen as *"A photo of the bill is needed
before this claim can be filed."* — never as "check your connection", never as a Python
argument error.

**And the rule applies on Desk too. Settled by Surbhi, 3 November 2026:**

> *"desk has to follow the same rules as the ESS portal mostly. it can't be exempted in
> this case."*

**This reverses my earlier reading**, which was that Desk was deliberately exempt and was
therefore the escape route when a bill does not exist. It is not exempt, and §3.1a is her
answer to the gap that leaves.

**The shape of the rule, which follows from how Frappe works and is not a caveat:**

| Surface | When the rule fires | Why |
|---|---|---|
| **ESS portal** | **At filing.** The form sends the file and the claim in one call | One call, so there is nothing to split |
| **Desk** | **At submit.** Save the draft, attach the bill, then submit | **Frappe renders the attachment area only on a document that has been saved** (`attachments.js` — `if (this.frm.doc.__islocal) … toggle(false)`). You cannot attach a file to a claim that does not exist yet, so "must have a file" cannot be checked at save |

**Two things follow, and both are improvements on my earlier draft:**

1. **The check belongs on the document, not in our portal endpoint.** A submit-time rule
   on `Expense Claim` also covers the REST API, data import and anything else that
   submits a claim. That is what "the same rules everywhere" actually requires, and it is
   stronger than enforcing it only in `apply_expense_claim`. The portal **also** refuses
   at filing, so the employee still gets the message at the moment they can act on it.
2. **A draft with no file stays a legal draft.** Only submitting is blocked. **HR saving
   a claim to finish later must not be refused** — say it in the spec, because a
   validate-time rule would break exactly that.

**Checked, so nobody has to re-derive it or fear it: a submit-time rule breaks no
automation.** Two paths in `hrms` create an Expense Claim without a person typing it, and
**neither inserts nor submits** — both build the document and hand it back for a human to
complete: `vehicle_log.py` L71–79 (`frappe.new_doc("Expense Claim")` … `return
exp_claim.as_dict()`) and `expense_claim.py` L726–738 (`get_expense_claim` for an
Employee Advance, same shape). **Confirmed.**

### 3.1a What happens when there genuinely is no bill

With Desk no longer exempt, there had to be a real answer for cash spent with no receipt
— an autorickshaw fare, a roadside puncture repair. Otherwise the honest outcomes are the
staff member losing their money, or somebody photographing something misleading to get
past the rule.

**Settled by Surbhi, 3 November 2026: the rule is "a file", not "a receipt."** Where no
bill exists, **HR attaches a signed self-declaration from the employee** stating what was
spent and why there is no bill.

So the mandatory rule stays absolute and reality still has a path. Two things about it:

- **This is documentation and a release-note line. There is no code.** No declaration
  type, no template, no flag, no form. The product sees a file; the organisation decides
  what is in it.
- **It leaves a better audit trail than a faded thermal receipt** — a dated statement in
  the employee's own words, signed, attached to the claim it belongs to.

### 3.1 Claims already in flight — expense only

My recommendation, and the reason:

| Case | Recommended rule | Why |
|---|---|---|
| Claims **already submitted** and waiting for an approver | **Leave them alone.** They stay decidable with no file | The rule fires at submit, so a claim already submitted never meets it. A rule applied backwards would strand a person's money in a queue nobody may approve |
| Claims **already approved or paid** | Untouched | Nothing to fix |
| Claims the employee has **half-filled in the browser** and not sent | They will hit the new rule when they press send, and the form will say so before they do | Nothing is saved until send, so there is no draft to rescue |
| **Desk drafts that exist today with no file** | They **stay saveable.** They cannot be **submitted** until a file is attached | A draft is a working document. Blocking the save would stop HR finishing a job they started |
| New claims from the day it ships, on either surface | Rule applies | — |

There is no "draft expense claim" an employee can save in the portal today — the modal
sends or it does not (**Confirmed**: `submitExpenseClaim` → one call).

### 3.2 One megabyte — and why that is not a camera requirement

**Settled by Surbhi, 3 November 2026: *"File size not more than 1 mb".*** The 5 MB from
slice 078 is superseded here.

**Bad news first, because it decides the design: a photograph from a current phone is
typically 2–5 MB.** If 1 MB were enforced on the raw file the camera produced, **a large
share of honest bill photos would be refused, and a driver standing at a pump has no way
to shrink a photo from his phone.** That would turn the mandatory field into a wall —
the exact failure we avoided on the regularization side. So:

> **1 MB is a cap on what we store, reached by compressing the picture. It is never a
> requirement placed on the employee's camera.**

| | Rule |
|---|---|
| **Images** | Accept whatever the camera sends (up to the site's own body limit). **Resize and recompress first — reusing `employee_photo.py`'s single Pillow call, which resizes and strips hidden data in one pass — then apply the 1 MB cap to the result.** A bill photographed at a sensible width lands well under 1 MB, so in practice nobody is refused. The width must keep the amount legible; that one number is DevOps' to set, not mine |
| **PDF** | **Cannot be recompressed that way**, so it gets its own, larger cap: **3 MB.** A scanner-produced or two-page bill from a petrol company or a hotel legitimately exceeds 1 MB, and a hard 1 MB would refuse it with no recourse. **Settled by Surbhi, 3 November 2026 — her word: "ok".** Two constants, no settings screen |
| **The refusal, whatever it is** | Comes from the **server**, in plain English, and **names the actual limit and what to do**. Never "upload failed", never "check your connection". Example wording: *"That file is 3.4 MB after we shrank it, and the limit is 1 MB. Please photograph the bill on its own, closer in."* |

**So the whole rule is two numbers: 1 MB stored for an image, 3 MB for a PDF.** Neither
the driver with a camera nor the office manager with an emailed invoice hits a wall. PDF
stays the one type we cannot strip hidden data from — that residual is unchanged and is
named for the security engineer in §9.

### 3.3 Where a medical bill goes — the routing answer

**Settled by Surbhi, 3 November 2026.** This replaces the warning-line recommendation
that stood in the first two drafts. **It is a better answer than either of the ones I
proposed, because a manager no longer opens a medical receipt at all, rather than being
warned that they are about to.**

**The mechanism: a ROLE is named on the Expense Claim Type, per company.** Her words,
3 November 2026: *"approver as well should be a role."* **This supersedes the named user
we settled earlier the same day.** The per-type, per-company shape stays; what is named
changes from a person to a role.

| | |
|---|---|
| **A type with a role named for that company** | The claim goes to **whoever holds that role** at that company. HR routes anything they judge sensitive — medical, legal, anything else — without coming back to us for code |
| **A type left blank** | The claim goes to **the employee's own manager, exactly as today.** Nothing changes for fuel, travel or stationery |
| **There is no "sensitive" tick** | Naming a role *is* the routing. That **drops a field rather than adding one** |

**A role is better than a person, and not merely different.** A named approver goes on
leave or leaves the company, and claims pile up behind them. A role does not.

**Why routing genuinely keeps the manager out, and is not a hidden column.** Verified in
the code: a claim carries one approver, set at creation by our own
`hr_api.apply_expense_claim` via `expense_approver_for(emp.name)` (L2408, L2451), Frappe
HR shares the claim only with that user, and the approver's queue finds claims by
`expense_approver == who.user` **alone** (`inbox_api._part_expense_approvals` L575). So
changing who the claim is addressed to changes who can see it — including its attachment.

**Per type per company**, following a shape the standard doctype already has.
**Confirmed:** `Expense Claim Type` carries an `accounts` child table of
`Expense Claim Account` rows keyed by `company` (`expense_claim_type.json` L36–39;
`expense_claim_account.json` has `company` + `default_account`, `istable: 1`). The
approver row belongs in the same shape, so a tenant with several companies does not end
up with one approver for all of them. And the lookup already runs:
`_expense_claim_accounts(company, expense_type)` (L2358) reads exactly that row.

#### ⚠ This is the one part of slice 081 with real design risk

**Everything else in this slice is reuse of something that already exists. This is not.
It changes a standard Frappe approval flow — the single named approver — and the design
gate must not wave it through as a small field change.** It needs **the business
analyst's spec and the engineer's impact analysis before any code.**

The constraint, stated so nobody assumes it away: **`Expense Claim.expense_approver` is a
single Link to User**, Frappe HR shares the document with that one user, and our queue
filters on equality with the caller. **A role is several people, so something has to
give.** Two options were put to Surbhi:

| | Option | Outcome |
|---|---|---|
| **Chosen** | The claim is **visible to everyone holding the role**, scoped to the claim's company, until someone acts. **The person who acts is recorded as the approver at that moment** | Keeps the leave problem solved. Needs a role-scoped queue beside the named-approver one |
| Rejected | Resolve the role to one user at filing | Keeps Frappe's model untouched, but the pick is arbitrary and the leave problem comes straight back |

**I am not designing the mechanism. Two facts for the BA and the engineer:**

1. **We have precedent in our own code, and it is close.** Slice 063 already replaced a
   named approver with a role-scoped queue for one case: `_with_hr_lwp` /
   `hr_lwp_filters` (`inbox_api.py` L436–476) composes the filters as
   `[named, "or", hr]`, where the HR branch is gated on
   `{"HR Manager", "HR User"} & set(frappe.get_roles(user))` and scoped with
   `permitted_companies` and `permitted_branches` **in the query, never as a list of
   employee ids**. The same file also carries role-scoped HR queues at L441/L464.
   **Confirmed** — point the BA here first.
2. **Frappe roles are not company-aware.** "Approver role per company" therefore means
   *the role named on the type for that company*, **plus** scoping to users whose own
   employee company matches the claim — the same scoping the existing HR queue does.
   **Nobody may assume a role carries a company.**

**Two things the spec must say out loud, not leave implied:**

1. **A route with nobody behind it must fail at filing, in plain words.**
   `expense_approver_for` already returns `None` for a disabled login or no Active
   Employee record, and `apply_expense_claim` already throws *"Your expense claim could
   not be filed because nobody is set to approve it. Ask HR to set your approver."*
   (**Confirmed**, L2408–2411). **A role with no holder at that company must behave the
   same way** — reuse that path and that tone. It must never let a claim vanish into a
   queue nobody reads.
2. **A mixed claim filed on Desk still carries one route.** HR can put a medical line
   next to a fuel line on one Desk claim, and that claim goes wherever it is addressed.
   **Our portal cannot produce a mixed claim — it sends one type** (**Confirmed**: the
   modal has a single Type field and `apply_expense_claim` builds one `expenses` row).
   This is a **known limit with no code against it.** We do not design for it.

### 3.4 The same problem on regularizations — and why the answer is different

**Settled by Surbhi, 3 November 2026 — her word: "I agree".**

**The gap, which nothing in the earlier drafts covered.** Routing solved the medical
receipt on expense claims. **The same problem exists on attendance regularizations and
had no answer.** Verified in `attendance_correction.py`: a regularization is reviewed by
the employee's **own manager** through `_reports_to` (L370, L421) and by HR, and **there
is no routing by reason** — the form carries a fixed reason list plus free text. So once a
file control exists there, **an employee attaching a doctor's note for a missed punch
hands it straight to their line manager.** And a doctor's note is the natural evidence for
a missed punch, so this is **more** likely there than on an expense claim, not less.

**Her decision: a plain line on the form, and nothing more.**

> *"your manager will see anything you attach here"*

The exact wording is the UX designer's to settle. **The obligation is that the form says
it plainly, before the person chooses a file** — not after, and not in a help panel.

**The principle that makes the two halves differ, so this does not read as an
inconsistency:**

> **A warning is fair when the person has a choice. It is not when we compel the upload.**

On an expense claim **we force the file**, so a warning would have shifted our
responsibility onto the employee — hence routing. On a regularization **the attachment is
optional and the employee keeps the choice**, so telling them the truth plainly is
enough, and it respects their judgement rather than overriding it.

**Her earlier decision — *"leave it non mandatory for attendance request"* — is what
makes this warning honest. Anyone who later makes that attachment mandatory must reopen
the routing question. It does not carry over.**

**For the security and privacy engineer: this is a transparency control, not an access
control**, and it must be verified as one — that the notice **is present and is shown
before the file is chosen**. **It must never be recorded as a protection. Nothing
restricts the manager here, by design.**

**No routing on regularizations.** No approver field, no role, no reason-level
configuration. It is on the do-not-build list in §8.

---

## 4 · Three ways to solve it, and the smallest move

| | What it is | Verdict |
|---|---|---|
| **Conventional** | A new child table "Claim Attachments", a settings page for allowed types and sizes per Expense Claim Type, a gallery viewer, a retention job of its own | **No.** A new DocType, a new settings page and a new dashboard are all on the banned list, and I cannot name what any of them buys here |
| **Better** *(recommended)* | One file control on each form, reusing `upload_file` + the existing stream-and-log pattern. One file. The file becomes a standard Frappe `File` attached to the document, so Desk shows it with no extra code. One extra line in the approver's queue: **"Bill attached — view"** | **Yes** |
| **Reimagined** | Read the amount and date off the photo and pre-fill the claim | **No.** AI where a well-placed field does the job. The person knows the amount; they are standing at the pump |
| **Could we not build it at all?** | Ask staff to WhatsApp the bill, as now | **No** — it leaves no record on the claim, which is the whole purpose. But a real smaller move exists and I took it: **one file, not many; no configuration; no new screen** |

---

## 5 · Kano and demand

| Feature | Class | Basis |
|---|---|---|
| Attach a bill to an expense claim | **Must-be** — **no longer a proxy** | **seen:** DTC shared the requirement and said the amendment is what makes the expense module worth using (Surbhi, 3 Nov 2026). Every comparable product ships it; its absence is the first thing a finance person asks about. Zoho People, Keka and Darwinbox all attach receipts to a claim — `[recall — verify]`, and I did not re-check release notes for this brief. Frappe HR's own Desk form has it (**Confirmed**), which is the sharpest evidence: our portal is *behind our own stack* |
| Attach evidence to an attendance regularization | **Performance** `proxy` | Not a standard doctype anywhere, so nobody is compared on it. More is better: a punch slip or a gate-register photo makes HR's decision faster |

A Must-be gap earns its place first. It also explains why this slice is worth doing and
is **not** a feature-parity race (product-context §6, item 10): we are closing a hole in
our own employee surface, not matching a module count.

**What we will deliberately NOT do that they all do:** no receipt gallery, no OCR, no
mileage-and-policy engine, no per-claim-type document rules, no "attach up to 10 files".
One bill, one tap, visible to the person who decides. That is better for a driver with a
2 GB phone on a 3G connection than a gallery he cannot load.

---

## 6 · Persona enhancements through the portal

| Persona | What the portal does for them here | Job it serves | In this slice? | Why |
|---|---|---|---|---|
| **Employee** | "Take a photo of the bill" in the claim form; the photo shows as a thumbnail before they send | Get my money back without a paper chase | **Yes** | It is the slice |
| **Frontline employee** | Camera opens directly, one file, works on a slow network, Hindi label | Claim at the pump, in 30 seconds | **Yes** | The primary user |
| **Line manager / approver** | "Bill attached — view" on the queue row; one tap shows the picture | Decide without asking | **Yes** | Without it the upload is pointless |
| **HR Manager** | The same file in the Desk sidebar, with no new screen | Audit and payment | **Yes — for free** | It is a standard `File` row |
| **CXO** | Nothing | Summaries | **No** | No purpose named |
| Employee, regularization | "Add a photo or document if you have one", **with a plain line saying the manager will see it** | Show the punch slip, and know who will read it | **Yes** | Optional, so it never blocks — and the notice is what makes "optional" an informed choice (§3.4) |
| HR deciding a regularization | "Evidence attached — view" on the queue row | Decide faster | **Yes** | Same rule: no upload without a reader |

---

## 7 · The WOW

**The approver's queue row.** Today it reads:

> Ramesh Kumar · Fuel · 28 Oct · ₹420 · *waiting 3 days*

After this slice, the same row carries one more line, and the word is deliberately the
plain one:

> **Bill attached — view**

Tap it and the photograph fills the screen. No download, no new page, no Desk. The
manager approves from the queue without ever asking a question. That is the moment: **a
claim stops being a number you have to trust.**

---

## 8 · Thin slice, and what is out

**In (needed to validate this now):** one file on the portal expense claim form,
mandatory, refused on the server with plain words · **a submit-time check on
`Expense Claim` itself, so Desk, the REST API and data import obey the same rule** (§3) ·
one file on the portal regularization form, optional · a "view" line on the approver's expense queue row and on the
regularization queue row · the file stored as a private Frappe `File` attached to the
document · **images resized and stripped on the way in, then capped at 1 MB stored**
(§3.2), PDF accepted as it is · one access-log row per viewer per file per day, reusing
the existing table · **one plain line on the regularization form, before the file picker,
saying the manager will see what is attached** (§3.4) · **an approver role named per company on an Expense Claim Type, and
the claim going to the holders of that role instead of the employee's manager** (§3.3),
with the existing "nobody is set to approve it" refusal reused when the role has no
holder.

**The honest note on size:** the attachment half of this slice is reuse and is small. The
approver role is not, and it is the part that decides whether 081 stays one slice. **If
the BA's spec or the engineer's impact analysis shows the role flow is bigger than the
attachments, the right move is two slices, not a phase 2.** Each stands alone: the
attachments are a complete outcome without the routing (claims go to the manager, as
today), and the routing is a complete outcome without the attachments. **That is a
recommendation for the design gate, not a decision I am taking** — and until she takes
it, this brief covers both.

**Before it can ship:** the per-file ceiling actually applied on dev and then production
(slice 078's OPS-24/52, still outstanding, now at **1 MB**) · the door tests from
`data-doors.md` as a plain staff login through the API.

**Worth doing later:** more than one file · evidence on leave applications · a "claims
missing a bill" report.

**Not doing:** OCR or amount extraction · per-claim-type *file* rules · a settings page ·
a new DocType · **a "sensitive" tick** (naming the approver is the routing) · a retention
job of its own · **a self-declaration type, template, flag or form** (§3.1a — the product
sees a file; the organisation decides what is in it) · **routing for attendance
regularizations** — no approver field, no role, no reason-level configuration (§3.4) ·
designing for a mixed Desk claim ·
thumbnails in a gallery · attachment on the goal/evidence flows (already has one).

**Run-side reality.** The 1 MB stored cap largely answers this before DevOps arrives: a
400-person tenant filing, say, 300 claims a month adds at most ~300 MB a month, and in
practice far less once images are recompressed. `evidence required` for the exact figure
and for the one number I will not guess — **the width images are resized to**, which has
to keep a printed amount legible (the 512 px used for profile photos is too small for a
bill). **If DevOps says storage growth is still material, the fix is a smaller re-encode,
not a smaller slice.**

---

## 9 · Access expectations — who should see this, and why

New data this slice creates: **a file an employee supplied as evidence** (a bill, a punch
slip — and sometimes, unavoidably, a medical receipt or an identity document), plus its
metadata (file name, who uploaded it, when).

| Data | Employee (own) | Frontline employee | Line manager / expense approver | HR Manager | CXO | Finance | Outside party (auditor, agency) | Class |
|---|---|---|---|---|---|---|---|---|
| **Bill on their own expense claim** | **See** · **change** until decided · not share. Purpose: it is their claim and their money | Same, on a phone | **See only the claims where they are the named approver**, for the one purpose of deciding that claim — which for an untyped claim is their own reporting line. **Not** change, **not** bulk-download | **See** across their own companies, for payment and audit. May correct | **No.** Summaries only — no purpose named | **See** for the claim they pay | **Only** through an HR export, with a purpose recorded | **Kano-must** |
| **Evidence on their own regularization** | **See** · **change** until decided | Same | Direct manager who vouches for the day, that person only | **See** across their companies | **No** | **No** | **No** | **Kano-must** |
| **A regularization file that contains health data** (a doctor's note for a missed punch) | Theirs, and **theirs to choose** — the attachment is optional | Same | **Sees it. Not routed away.** The control is a **notice before the file is chosen**, not a restriction (§3.4) | **See** | **No** | **No** | **No** | expectation |
| **File metadata** (name, uploader, time) | See own | See own | With the file | See | No | With the claim | With the export | expectation |
| **Who looked at my file** | **Should be answerable** — reuse the existing log | Same | — | May read the log | No | No | No | expectation |
| **A file that turns out to contain health, bank or ID data** | Theirs | Theirs | **Not theirs — routed away.** HR names an approver role on that claim type, and the line manager does not hold it, so the claim never enters their queue (§3.3) | See, with care, for payment | **No** | — | — | **Kano-must** |
| **A claim routed to a role** | Theirs | Theirs | Only if they hold the role **and** are in the claim's company | **See** for payment and audit | **No** | **See** for the claim they pay | HR export only | **Kano-must** |

### The counsel conflict, and how it is resolved

The first two drafts of this brief carried an unresolved conflict here: **mandatory on
expense claims means a line manager would sometimes open a medical receipt**, and
counsel's advice of 1 November is that **health and passport data are not for managers.**

**It is resolved, and resolved properly — not with a warning.** Surbhi settled it on
3 November with the routing in §3.3: HR names the approver on a sensitive claim type, per
company, and the manager is never that person. **A manager does not open a medical
receipt at all, rather than being warned that they are about to.** That is the answer
counsel's advice actually asks for; a warning would have left the data where it was and
moved the responsibility onto the employee.

**For the security and privacy engineer: the control is now a routing control, so verify
it as one.** The test is that the **manager's queue genuinely cannot return a routed
claim** — through `/api/resource/Expense Claim`, `frappe.desk.reportview.get`, report
view and export, link search, and share — **not** that a warning appears. As a plain
staff login, through the API, on a fresh site.

**And the role version widens what you have to prove.** With a named user, the only thing
standing between a manager and a routed claim was the `expense_approver` field and the
DocShare Frappe HR creates from it. With a role, there is a second question: **can a
role-holder at another company see the claim?** Frappe roles are not company-aware
(§3.3), so the company scoping *is* the control, and it must live in the permission layer
and the query — not in the portal screen.

**And one control in this slice is deliberately not an access control.** On attendance
regularizations the manager **does** see what is attached, by design, and the control is
a **notice shown before the file is chosen** (§3.4). **Verify it as a transparency
control — that the line is present and comes before the file picker — and never record it
as a protection.**

### The five data-doors questions, answered at product level

1. **Who can read it, and which Frappe door stops everyone else?** The person it belongs
   to, the named approver of that document, and HR within their own companies. The door
   must be the permission layer on the **parent document** — not the portal screen, and
   not the child row (a `has_permission` on a child table answers False for everybody).
   The existing pattern is the model: the browser is **never** handed a
   `/private/files/...` URL; a guarded endpoint streams the bytes. **Note the honest
   half, already documented in this product: a reader who somehow holds a private-file
   URL can still fetch it, because Frappe's private-file gate falls back to the parent's
   read permission and fires no hook.** Nothing in this slice may claim otherwise.
2. **Tested as a plain staff login through the API?** Must be — `/api/resource/File`,
   `frappe.client.get_list` on File, `frappe.client.attach_file`, report view and export,
   and share/assign on the claim. A staff login must not be able to list other people's
   files.
3. **Fresh site, and real-tenant counts?** Yes, both, before release.
4. **How many bypasses?** My expectation is **zero new** ones. Note that today's
   `apply_expense_claim` already uses `doc.insert(ignore_permissions=True)` (**Confirmed**,
   L2446) — that is existing, counted, and this slice must not add to it.
5. **What could a manager with a self-service role change or share?** The answer must be
   *nothing of somebody else's* — and "share" is the dangerous verb: sharing a claim opens
   its attachments to whoever it was shared with.

**For the security and privacy engineer — questions I am not answering:**

- How long is an evidence file kept, and against which of counsel's two retention clocks?
- Is opening someone's bill logged, and is the employee able to ask who looked?
- Mandatory raises exposure, it does not lower it: **every** expense claim will now carry
  a file, so volume and the chance of identity or medical documents arriving both go up.
  Does that change the retention answer?
- PDF is the one type we cannot strip. Accept, or images only?
- What happens to the file when the claim is cancelled, or the employee leaves?

---

## 10 · Regulatory read

1. **Which regime?** Data protection — DPDP, and GDPR where EU exposure is real. Not AI,
   not employment law.
2. **Whose obligation?** The employer's — our customer's. This slice helps them discharge
   it: an expense record with its evidence attached, in one place, with a retention clock,
   is what an audit asks for. It also *adds* personal data to our systems, so it is our
   processor duty to hold it properly.
3. **What becomes possible that was not?** New personal data collected (employee-supplied
   documents, at volume), and **new visibility granted — a line manager can now open a
   document their report photographed, except where the claim type routes it away from
   them.** Both are compliance events.
4. **The honest downside.** The sentence we did not want on a front page was *"HR app
   makes employees photograph medical bills for their manager to read."* **That sentence
   is no longer true of this slice** — §3.3 routes a sensitive claim type to a named
   approver, so the manager never receives it. What remains defensible-but-worth-saying:
   HR holds more employee-supplied documents than before, which is why §9's retention and
   logging questions (D6) are still open.

---

## 11 · Thriving-workplace lens

| Lens | Answer |
|---|---|
| **Engagement** | Yes — a driver gets paid back without chasing anyone. Agency and momentum, in the same minute |
| **Collaboration** | Yes — the employee's evidence becomes the approver's answer, at the moment the approver is deciding |
| **Inclusiveness** | **The risk is here.** A mandatory bill assumes a camera, light, a network and literacy. A shared phone makes it worse. The label must be in Hindi too, one file only, and the failure must say what to do next. **The self-declaration route (§3.1a) is what keeps a person who has no bill from losing their money — so HR knowing about it is an inclusiveness requirement, not an administrative footnote** |
| **Transparency** | It makes the evidence behind a payment visible to the person who approves it — which is fair — **and no further.** A sensitive claim type goes to an approver role instead of the line manager (§3.3). On a regularization the employee is **told, before they choose**, that their manager will see the file (§3.4). Nothing here lets anyone rank or monitor an individual |

---

## 12 · Success criteria

| Measure | Baseline | Target | How instrumented |
|---|---|---|---|
| Share of portal expense claims with a readable bill attached | 0% (**Confirmed** — impossible today) | 100% of new claims (it is mandatory) and **≤2% refused twice in a row**, which is the real test: a person failing repeatedly means the control is too hard | Count of claims; count of server refusals per user per day |
| **Uploads refused for size after compression** | 0 (new) | **≈0.** Anything above a handful means §3.2's compression is set too conservatively, not that staff are doing it wrong | Count the size refusal separately from every other refusal |
| Days from claim filed to decided | **baseline unknown — measure first** from `creation` to `approval_status` change | Down by a third | Existing fields; no new data |
| Approvers who open the file before deciding | n/a | ≥70% in the first month | The access log already records one row per viewer per file per day |
| Regularizations with evidence attached (optional) | 0% | **No target.** Watched only, as a signal of whether it helps | Same count |

Not measured: logins, page views.

---

## 13 · Risks and the honest downside — red-teamed

| Question | Answer |
|---|---|
| **10x the data?** 442 staff at DTC; every claim will now carry a file | The 1 MB stored cap bounds it. Re-encode images smaller if needed. Do not raise the cap |
| **The 1 MB cap refuses honest photos?** The sharpest risk in the slice | Answered by design: compress first, cap second (§3.2). **A test must prove it with a real 4 MB phone photo, not a 200 KB fixture** |
| **Bad or missing data?** A photo too dark to read, or a PDF that is really a 40-page statement | The approver can decline with a reason — that path already exists (`decline_reason`, **Confirmed**) |
| **The employee cannot produce a bill at all** — cash for an autorickshaw | **The rule is "a file", not "a receipt."** HR attaches a signed self-declaration from the employee (§3.1a). No code; **HR must know this is the route**, so it goes in the release note and the documentation |
| **Desk is not exempt, so could HR be blocked mid-job?** | No. The rule fires at **submit**, not at save, so a draft stays a working document (§3) |
| **A future slice makes the regularization attachment mandatory** | **Then the warning in §3.4 stops being fair and the routing question returns.** A warning is only honest while the employee has a choice. **Named here so the decision cannot drift silently** |
| **Employee leaves / approver changes mid-flow?** | The file follows the claim, not the person. Already true of `expense_approver` |
| **The role named on a claim type has nobody holding it at that company** | **Must refuse at filing, in the words that already exist** — *"nobody is set to approve it. Ask HR to set your approver."* Never a claim sitting in a queue nobody reads (§3.3) |
| **Several role-holders open the same claim at once** | Two people deciding one claim is a new failure the named-approver model never had. **The BA and the engineer must answer it; I am not designing it** (§3.3) |
| **A role-holder outside the claim's company** | Frappe roles are not company-aware. The scoping is the control, and it must live in the query, as the existing HR queue does (§3.3) |
| **A mixed Desk claim — a medical line beside a fuel line** | It carries one route and goes wherever it is addressed. **A known limit, with no code against it.** The portal cannot produce one: it sends a single type |
| **HR creates an expense type and forgets its account** | Already refused at filing with a message naming what to set (§1.4). The fix is a release-note line, not code |
| **Upgrade and migration?** | Nothing migrates. No backfill. Old claims stay as they are |
| **Configured wrong?** | Two things, both with safe blanks. A blank approver on a claim type means "the employee's manager, as today", so an untouched tenant behaves exactly as before. The file caps are constants, not settings. **The one way to get it wrong is naming a role nobody at that company holds** — covered two rows down |
| **Support tickets this would create** | "My photo will not upload" (size, HEIC from an iPhone, no network), and "I cannot file my claim" — which is the mandatory rule working. Both are answered by the refusal message, so the wording is not cosmetic |
| **Cheapest way to find out before building** | Ask one DTC supervisor to send five real bills as they would photograph them. Look at the size, the format and whether the amount is legible. One afternoon |

---

## 14 · Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| **D1** | **Expense claims already submitted with no bill** — leave them decidable (my recommendation, §3.1) or hold them? | Surbhi | The spec's rule set |
| **D6** | Retention clock and logging for evidence files | Security/privacy engineer, with counsel | Spec |

That is the only decision open. §0's flag still stands: `01a-ux-opportunities.md` and
`07-devops-inputs.md` §1 do not exist for 081, so **the design gate should wait for
them.**

**Closed since the first draft** — recorded so nobody re-opens them:

| # | Decision | Her words / outcome |
|---|---|---|
| D1 | Claims already in flight | Narrowed to expense only; recommendation in §3.1 stands for the spec |
| **D2** | **No HR-configurable rules.** One fixed behaviour — one file, images or PDF, mandatory on claims and optional on regularizations | She agreed with the recommendation |
| **D5** | **File size 1 MB**, superseding slice 078's 5 MB | *"File size not more than 1 mb"* |
| **D5b** | **3 MB for PDF**, 1 MB for images (§3.2) | *"ok"* — approved as recommended |
| **D7** | **DTC files expense claims and asked for this** | *"they shared the requirement and also asked for these amendments to make it worth their usage"* |
| **D3** | **The medical receipt routes away from the manager.** The approver is named on the Expense Claim Type, per company; blank means the employee's own manager as today; no "sensitive" tick (§3.3) | Settled 3 Nov 2026. **My warning-line recommendation is superseded and withdrawn** |
| **D3b** | **The approver is a ROLE, not a named user** — per type, per company. Visible to everyone holding the role at that company until someone acts; the person who acts is recorded as the approver (§3.3) | *"approver as well should be a role."* **Supersedes the named user in D3** |
| **D4** | **Desk is NOT exempt.** The rule fires at **submit** on Desk and at filing in the portal; a draft with no file stays a legal draft; the check belongs on the document, not only in our endpoint (§3) | *"desk has to follow the same rules as the ESS portal mostly. it can't be exempted in this case."* **This reverses my earlier reading** |
| **D4b** | **"A file", not "a receipt."** Where no bill exists, HR attaches a signed self-declaration from the employee (§3.1a) | Approved 3 Nov 2026. Documentation and a release-note line, **no code** |
| **D9** | **A plain line on the regularization form — *"your manager will see anything you attach here"* — and no routing there** (§3.4). The principle: a warning is fair when the person has a choice; it is not when we compel the upload | *"I agree"* |
| **D8** | **HR adds their own expense types** | *"we need to allow the administrator to add expense types themselves according to the organisation context"* — **already works** (§1.4). A release-note line about the two-step set-up, no code |

## 15 · Assumptions

- `[ASSUMPTION]` The ESS portal is the only phone surface that needs this — the field
  app is check-in only. Checked `field_app_records.py`; **Confirmed** for that file,
  assumed for the app as a whole.
- `[ASSUMPTION]` One file per form is enough. A claim is one bill at DTC.
- `[ASSUMPTION]` Competitors all attach receipts (§5) — `[recall — verify]`, not
  re-checked for this brief.
- `[ASSUMPTION]` "Attachment field" in her words means a file on the form, not a
  specific Frappe `Attach` fieldtype. The standard Frappe attachment is cheaper and
  shows on Desk for free.

## 16 · Kill criteria

- **Five real bills from DTC come back unreadable once compressed to under 1 MB.** Then
  the mandatory rule produces evidence nobody can use, and this is the wrong control. This
  is now the first thing to test, because the cap is tighter than the first draft assumed.
- DevOps shows storage growth that needs a new store or a job. Then the slice has outgrown
  its value and should shrink to optional on both forms.
- **The approver role turns out to need changes to how Frappe shares or submits an Expense
  Claim.** Then it is not a field change, it is a workflow change, and it should be its own
  slice with its own gate — the attachments ship without it (§8).
- Counsel says a line manager may not see an employee-supplied document at all. Then the
  expense half routes to HR and the WOW moment moves — and that is a different slice.

---

## 17 · Subtract pass — what I removed

Read once more asking only what could go. Removed: a per-claim-type rules table; an HR
settings page for file types and sizes; multiple files per claim; a thumbnail gallery; a
"claims missing a bill" report; a retention job of its own (the existing log and clock
are reused); evidence on leave applications; a mandatory rule on Desk; and OCR. Also cut
the escape-hatch design for "the employee has nothing to photograph" — her revised
decision made the attendance form optional, so it is no longer needed, and on the expense
side the existing Desk route already is the escape.

**What is left is: one file control on two forms, one view line on two queue rows, one
compress-then-cap step, one server refusal, one log row, and one Custom Field for the
approver role.**

**Second pass, after her 3 November decisions.** D2 closed the configurable-rules
question, so the whole settings discussion is gone rather than parked. D7 removed a
caveat and a question. I added nothing new except §3.2 — and §3.2 is not an extra
feature: it is the existing `employee_photo.py` call reused, which is what makes the
1 MB figure survivable instead of a wall.

**Third pass, after D3 and D5b.** Deleted my own warning-line recommendation and the
three-option conflict section it sat in — superseded, and a warning would have moved the
responsibility onto the employee rather than fixing anything. §3.3 **drops a field** as
well: there is no "sensitive" tick, because naming an approver on a claim type *is* the
routing. Also removed the PDF option list now that the number is settled.

**Sixth pass, after D9.** One line of copy and one principle. I added **no** mechanism on
the regularization side — no approver field, no role, no reason-level configuration — and
put "routing for attendance regularizations" on the do-not-build list so the expense-claim
answer cannot be copied across by reflex. The principle in §3.4 is there to stop a future
reader "fixing" the inconsistency.

**Fifth pass, after D4 and D4b.** Nothing added but the rule's shape. D4 made the slice
**smaller to describe and stronger**: one submit-time check on the document replaces a
portal-only check plus a Desk exemption plus the paragraph explaining the exemption, and
it covers the REST API and data import for free. D4b removed work rather than adding it —
a self-declaration is a file like any other, so there is no declaration type, template,
flag or form, and that is now on the do-not-build list. I also deleted my own
"ask HR to file this claim for you" fallback wording, which the closed exemption made
untrue.

**Fourth pass, after D3b and D8.** D8 removed scope rather than adding it: the
expense-type request was already delivered, so §1.4 records it as done and the only
output is a release-note line. D3b replaced a field value with a different field value —
a role instead of a user — and removed a weakness (a named approver on leave) rather
than adding a feature. I deleted nothing else, and I deliberately did **not** design the
role queue: naming the chosen option and pointing at slice 063's precedent is the whole
of my job there.

The slice as it stands: **one file control on two forms, one compress-then-cap step, one
server refusal, one view line on two queue rows, one log row, one Custom Field for the
approver role — and one genuinely new flow (§3.3) that needs the BA and the engineer
before any code.**
